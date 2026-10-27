package scholarchain.build

import java.io.File
import java.nio.file.{Files, StandardCopyOption}
import java.util.jar.JarFile

/** A thin application JAR and its complete runtime JAR classpath. */
object ServiceDistribution {
  val artifacts: Vector[(String, String)] = Vector(
    "query-api" -> "edu.uic.cs441.scholarchain.services.QueryApiMain",
    "graph-service" -> "edu.uic.cs441.scholarchain.services.GraphServiceMain",
    "semantic-service" -> "edu.uic.cs441.scholarchain.services.SemanticServiceMain",
    "embedding-worker" -> "edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain"
  )

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
