package scholarchain.build

import java.io.File
import java.nio.file.{Files, StandardCopyOption}
import java.util.jar.JarFile
import scala.jdk.CollectionConverters._

/** A thin application JAR and its complete runtime JAR classpath. */
object ServiceDistribution {
  val artifacts: Vector[(String, String)] = Vector(
    "query-api" -> "edu.uic.cs441.scholarchain.services.QueryApiMain",
    "graph-service" -> "edu.uic.cs441.scholarchain.services.GraphServiceMain",
    "semantic-service" -> "edu.uic.cs441.scholarchain.services.SemanticServiceMain",
    "embedding-worker" -> "edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain"
  )

  /** Versioned runtime prompts and schemas remain ordinary files, preserving their paths. */
  def writePromptAssets(source: File, output: File): Unit = {
    val roots = Seq("runtime", "schemas").map(name => new File(source, name).toPath)
    val assets = roots.flatMap { root =>
      require(Files.isDirectory(root), s"Missing runtime asset directory: $root")
      val walk = Files.walk(root)
      try {
        val paths = walk.iterator().asScala.toVector
        require(!paths.exists(Files.isSymbolicLink(_)), s"Runtime assets contain a symlink: $root")
        val files = paths.filter(Files.isRegularFile(_))
        require(files.nonEmpty, s"Empty runtime asset directory: $root")
        files
      } finally walk.close()
    }
    val destination = new File(output, "prompts").toPath
    if (Files.exists(destination)) {
      val walk = Files.walk(destination)
      try walk.iterator().asScala.toVector.sortBy(_.getNameCount).reverse.foreach(Files.delete(_))
      finally walk.close()
    }
    assets.foreach { asset =>
      val target = destination.resolve(source.toPath.relativize(asset))
      Files.createDirectories(target.getParent)
      Files.copy(asset, target, StandardCopyOption.REPLACE_EXISTING)
    }
  }

  def write(appJar: File, dependencies: Seq[File], output: File): Unit = {
    require(appJar.isFile, s"Missing application JAR: $appJar")
    val jar = new JarFile(appJar)
    try
      artifacts.foreach { case (_, mainClass) =>
        require(
          jar.getJarEntry(mainClass.replace('.', '/') + ".class") != null,
          s"Missing artifact main class: $mainClass"
        )
      }
    finally jar.close()
    val distinct = dependencies.map(_.getCanonicalFile).distinct
    distinct.foreach(file =>
      require(file.isFile && file.getName.endsWith(".jar"), s"Not a runtime JAR: $file")
    )
    require(
      distinct.map(_.getName).distinct.size == distinct.size,
      "Runtime dependency JAR names collide"
    )
    val lib = new File(output, "lib")
    Files.createDirectories(lib.toPath)
    val existing = Option(lib.listFiles()).getOrElse(Array.empty[File])
    existing.foreach { file =>
      require(file.isFile, s"Unexpected directory in generated distribution: $file")
      Files.delete(file.toPath)
    }
    Files.copy(
      appJar.toPath,
      new File(output, "services.jar").toPath,
      StandardCopyOption.REPLACE_EXISTING
    )
    distinct.foreach { file =>
      Files.copy(
        file.toPath,
        new File(lib, file.getName).toPath,
        StandardCopyOption.REPLACE_EXISTING
      )
    }
  }
}
