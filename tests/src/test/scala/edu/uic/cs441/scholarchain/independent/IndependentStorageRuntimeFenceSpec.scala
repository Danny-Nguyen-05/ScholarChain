package edu.uic.cs441.scholarchain.independent

import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

class IndependentStorageRuntimeFenceSpec extends AnyFunSuite {
  private val runtime = Path.of("modules/services/src/main/scala/Runtime.scala")
  private val helper = Path.of("modules/storage/src/main/scala/RuntimeAssembly.scala")

  test("runtime scan permits GraphReader and ignores loader names in comments or inert strings") {
    val source = """import edu.uic.cs441.scholarchain.storage.GraphReader
      |// GraphLoader and NeptuneGraphLoader are administrative capabilities.
      |/* outer /* GraphLoader */ comment */
      |class Runtime(graph: GraphReader) {
      |  val description = "GraphLoader startLoaderJob"
      |}
      |""".stripMargin
    val result = RuntimeGraphFence.scan(
      Map(
        runtime -> source,
        Path.of(
          "modules/storage/src/main/scala/StoragePorts.scala"
        ) -> "trait GraphReader; trait GraphLoader",
        Path.of("modules/storage/src/main/scala/NeptuneGraphReader.scala") ->
          "class NeptuneGraphReader(client: NeptunedataClient) extends GraphReader"
      ),
      Set(runtime)
    )
    assert(result.inspected == Set(runtime) && result.findings.isEmpty)
  }

  test("runtime scan detects direct, renamed, fully qualified and raw SDK loader access") {
    val snippets = Vector(
      "class Runtime(loader: GraphLoader)",
      "import edu.uic.cs441.scholarchain.storage.{GraphLoader as Hidden}; class Runtime(x: Hidden)",
      "class Runtime(x: edu.uic.cs441.scholarchain.storage.NeptuneGraphLoader)",
      "import software.amazon.awssdk.services.neptunedata.*; class Runtime(x: NeptunedataClient)",
      "class Runtime { def apply(x: Any) = x.startLoaderJob() }"
    )
    snippets.foreach { source =>
      val result = RuntimeGraphFence.scan(Map(runtime -> source), Set(runtime))
      assert(result.findings.nonEmpty, source)
      assert(result.findings.forall(_.path == runtime))
    }
  }

  test(
    "runtime scan follows referenced storage composition and detects a hidden write capability"
  ) {
    val sources = Map(
      runtime -> "class Runtime { val assembly = RuntimeAssembly() }",
      helper -> "object RuntimeAssembly { def apply(): GraphLoader = new NeptuneGraphLoader() }"
    )
    val result = RuntimeGraphFence.scan(sources, Set(runtime))
    assert(result.inspected == Set(runtime, helper))
    assert(result.findings.exists(f => f.path == helper && f.capability == "GraphLoader"))
    val safe = RuntimeGraphFence.scan(
      sources.updated(
        helper,
        "object RuntimeAssembly { def apply(reader: GraphReader): GraphReader = reader }"
      ),
      Set(runtime)
    )
    assert(safe.inspected == Set(runtime, helper) && safe.findings.isEmpty)
  }

  test("character literals cannot hide a following graph write capability") {
    val literals = Vector("'\"'", "'\\\''", "'\\\\'", "'\\n'", "'x'", "'\\" + "u0022'")
    literals.foreach { literal =>
      val source = s"class Runtime { val c = $literal; val loader: GraphLoader = ??? }"
      val masked = RuntimeGraphFence.code(source)
      assert(masked.length == source.length)
      val result = RuntimeGraphFence.scan(Map(runtime -> source), Set(runtime))
      assert(result.findings.exists(_.capability == "GraphLoader"), source)
    }
  }

  test("interpolation retains executable expressions including nested braces and strings") {
    val snippets = Vector(
      "class Runtime { val text = s\"${new NeptuneGraphLoader()}\" }",
      "class Runtime { val text = raw\"${loader.startLoaderJob()}\" }",
      "class Runtime { val text = custom\"$GraphLoader\" }",
      "class Runtime { val text = s\"\"\"${new NeptuneGraphLoader()}\"\"\" }",
      "class Runtime { val text = s\"${ { val c = '}'; /* } */ loader.startLoaderJob() } }\" }",
      "class Runtime { val text = s\"${s\"${loader.startLoaderJob()}\"}\" }",
      "class Runtime { val text = s\"${\"}\"; loader.startLoaderJob()}\" }"
    )
    snippets.foreach { source =>
      val result = RuntimeGraphFence.scan(Map(runtime -> source), Set(runtime))
      assert(result.findings.nonEmpty, source)
    }
  }

  test("interpolation masks inert text, escaped dollars and inert nested expressions") {
    val snippets = Vector(
      "class Runtime { val text = s\"GraphLoader $$GraphLoader $safe\" }",
      "class Runtime { val text = s\"$${GraphLoader}\" }",
      "class Runtime { val text = s\"${\"GraphLoader\"}\" }",
      "class Runtime { val text = s\"${ { /* GraphLoader */ 1 } }\" }",
      "class Runtime { val text = raw\"\"\"GraphLoader $$GraphLoader\"\"\" }"
    )
    snippets.foreach { source =>
      val masked = RuntimeGraphFence.code(source)
      assert(masked.length == source.length)
      assert(RuntimeGraphFence.scan(Map(runtime -> source), Set(runtime)).findings.isEmpty, source)
    }
  }

  test("interpolated references still follow storage composition helpers") {
    val sources = Map(
      runtime -> "class Runtime { val text = s\"${RuntimeAssembly()}\" }",
      helper -> "object RuntimeAssembly { def apply(): GraphLoader = new NeptuneGraphLoader() }"
    )
    val result = RuntimeGraphFence.scan(sources, Set(runtime))
    assert(result.inspected == Set(runtime, helper))
    assert(result.findings.exists(f => f.path == helper && f.capability == "GraphLoader"))
  }

  test(
    "actual runtime roots and their referenced storage composition expose no graph write dependency"
  ) {
    val root = IndependentTestSupport.repoRoot
    val roots = Vector("modules/rag/src/main", "modules/services/src/main")
    def scalaFiles(relative: String): Vector[Path] = {
      val directory = root.resolve(relative)
      if (!Files.exists(directory)) Vector.empty
      else {
        val walk = Files.walk(directory)
        try
          walk
            .iterator()
            .asScala
            .filter(p => Files.isRegularFile(p) && p.toString.endsWith(".scala"))
            .toVector
            .map(root.relativize)
        finally walk.close()
      }
    }
    val runtimeFiles = roots.flatMap(scalaFiles).toSet
    val all = runtimeFiles ++ scalaFiles("modules/storage/src/main")
    val source = all.map(p => p -> Files.readString(root.resolve(p), UTF_8)).toMap
    val result = RuntimeGraphFence.scan(source, runtimeFiles)
    info(
      s"Runtime graph fence: runtimeSources=${runtimeFiles.size}, inspectedSources=${result.inspected.size}; heuristic only."
    )
    if (runtimeFiles.isEmpty)
      info(
        "rag/services have no runtime Scala source yet; detection is established by regression fixtures, not by runtime wiring."
      )
    assert(result.findings.isEmpty, result.findings.mkString("\n"))
  }
}
