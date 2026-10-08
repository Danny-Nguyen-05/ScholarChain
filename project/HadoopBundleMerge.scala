package scholarchain.build

import java.io.{BufferedOutputStream, File, FileOutputStream, InputStream}
import java.nio.charset.StandardCharsets
import java.nio.file.{AtomicMoveNotSupportedException, Files, StandardCopyOption}
import java.security.MessageDigest
import java.util.jar.{JarEntry, JarFile, JarOutputStream}

import scala.collection.mutable

/** Shared by the sbt task and its build-verification tests. An assembly cache may already contain a
  * previous core overlay, so current core content must own collisions and deleted core entries.
  */
object HadoopBundleMerge {
  val CorePrefix = "edu/uic/cs441/scholarchain/core/"
  val OwnershipIndex = "META-INF/scholarchain-core-entries.v1"

  def merge(bundle: File, currentCore: File): Unit = {
    val temp =
      Files.createTempFile(bundle.toPath.toAbsolutePath.getParent, "core-overlay-", ".jar.part")
    var cached: JarFile = null
    var core: JarFile = null
    try {
      cached = new JarFile(bundle)
      core = new JarFile(currentCore)
      val currentNames = retainedNames(core)
      require(!currentNames.contains(OwnershipIndex), "core JAR uses reserved ownership inventory")
      val previousNames = previousOwnership(cached)
      val out = new JarOutputStream(new BufferedOutputStream(new FileOutputStream(temp.toFile)))
      try {
        val written = mutable.Set.empty[String]
        def copy(jar: JarFile, current: Boolean): Unit = {
          val entries = jar.entries()
          while (entries.hasMoreElements) {
            val entry = entries.nextElement()
            val name = entry.getName
            val previousCore =
              !current && (name.startsWith(CorePrefix) || previousNames.contains(name))
            if (
              !entry.isDirectory && !skipSignature(
                name
              ) && name != OwnershipIndex && !previousCore && !written(name)
            ) {
              written += name
              val next = new JarEntry(name)
              if (entry.getTime >= 0) next.setTime(entry.getTime)
              out.putNextEntry(next)
              val input = jar.getInputStream(entry)
              try transfer(input, out)
              finally {
                input.close()
                out.closeEntry()
              }
            }
          }
        }
        copy(core, current = true)
        copy(cached, current = false)
        val inventory = new JarEntry(OwnershipIndex)
        inventory.setTime(0L)
        out.putNextEntry(inventory)
        out.write(
          (currentNames.toVector.sorted.mkString("\n") + "\n").getBytes(StandardCharsets.UTF_8)
        )
        out.closeEntry()
      } finally out.close()
    } catch {
      case error: Throwable =>
        Files.deleteIfExists(temp)
        throw error
    } finally {
      if (core != null) core.close()
      if (cached != null) cached.close()
    }
    try {
      verify(temp.toFile, currentCore)
      try
        Files.move(
          temp,
          bundle.toPath,
          StandardCopyOption.ATOMIC_MOVE,
          StandardCopyOption.REPLACE_EXISTING
        )
      catch {
        case _: AtomicMoveNotSupportedException =>
          Files.move(temp, bundle.toPath, StandardCopyOption.REPLACE_EXISTING)
      }
    } finally Files.deleteIfExists(temp)
  }

  /** All current core classes/resources must match; removed classes must not linger in the cache.
    */
  def verify(bundle: File, currentCore: File): Unit = {
    var bundled: JarFile = null
    var core: JarFile = null
    try {
      bundled = new JarFile(bundle)
      core = new JarFile(currentCore)
      val expected = retainedNames(core)
      val actual = retainedNames(bundled)
      val expectedClasses = expected.filter(_.startsWith(CorePrefix))
      val actualClasses = actual.filter(_.startsWith(CorePrefix))
      require(
        actualClasses == expectedClasses,
        "dependency bundle core namespace differs from current core JAR"
      )
      expected.foreach { name =>
        val wanted = core.getJarEntry(name)
        val found = bundled.getJarEntry(name)
        require(
          found != null && !found.isDirectory,
          "dependency bundle missing current core entry: " + name
        )
        require(
          wanted.getSize == found.getSize && entryHash(core, wanted) == entryHash(bundled, found),
          "dependency bundle differs from current core entry: " + name
        )
      }
      require(
        previousOwnership(bundled) == expected,
        "dependency bundle core ownership inventory is stale"
      )
    } finally {
      if (core != null) core.close()
      if (bundled != null) bundled.close()
    }
  }

  private def retainedNames(jar: JarFile): Set[String] = {
    val names = mutable.Set.empty[String]
    val entries = jar.entries()
    while (entries.hasMoreElements) {
      val entry = entries.nextElement()
      if (!entry.isDirectory && !skipSignature(entry.getName)) names += entry.getName
    }
    names.toSet
  }

  private def previousOwnership(jar: JarFile): Set[String] = {
    val entry = jar.getJarEntry(OwnershipIndex)
    if (entry == null) Set.empty
    else {
      require(
        entry.getSize >= 0 && entry.getSize <= 1048576,
        "core ownership inventory exceeds its bound"
      )
      val input = jar.getInputStream(entry)
      try
        new String(input.readAllBytes(), StandardCharsets.UTF_8)
          .split("\n")
          .filter(_.nonEmpty)
          .toSet
      finally input.close()
    }
  }

  private def skipSignature(name: String): Boolean =
    name.startsWith("META-INF/") && (name.endsWith(".SF") || name.endsWith(".DSA") || name.endsWith(
      ".RSA"
    ))

  private def entryHash(jar: JarFile, entry: JarEntry): Vector[Byte] = {
    val digest = MessageDigest.getInstance("SHA-256")
    val input = jar.getInputStream(entry)
    try {
      val bytes = new Array[Byte](8192)
      var count = input.read(bytes)
      while (count >= 0) {
        if (count > 0) digest.update(bytes, 0, count)
        count = input.read(bytes)
      }
      digest.digest().toVector
    } finally input.close()
  }

  private def transfer(input: InputStream, out: JarOutputStream): Unit = {
    val bytes = new Array[Byte](8192)
    var count = input.read(bytes)
    while (count >= 0) {
      if (count > 0) out.write(bytes, 0, count)
      count = input.read(bytes)
    }
  }
}
