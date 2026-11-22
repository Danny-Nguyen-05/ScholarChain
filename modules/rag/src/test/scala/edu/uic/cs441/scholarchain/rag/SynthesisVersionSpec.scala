package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.security.MessageDigest
import org.scalatest.funsuite.AnyFunSuite

/** Review finding N1: a changed synthesis prompt or schema gets a new version label. The checked-in
  * synthesis-v2 files are pinned by hash so that an in-place edit fails here until the label, the
  * file name, the hash below and the core configuration are bumped together.
  */
class SynthesisVersionSpec extends AnyFunSuite {
  private val config = {
    val in = getClass.getResourceAsStream("/scholarchain.runtime-config.v1.json")
    val text =
      try new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8)
      finally in.close()
    RuntimeConfigLoader.fromJson(text).toOption.get
  }
  private val prompts: Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("prompts"))
    .find(Files.isDirectory(_))
    .get
  private def sha256(file: String): String =
    MessageDigest
      .getInstance("SHA-256")
      .digest(Files.readAllBytes(prompts.resolve(file)))
      .map("%02x".format(_))
      .mkString
  // Update these only together with a new synthesis version label (see the class comment).
  private val promptSha256 = "0d9c6c16abd9b64ec372270595bc50c8398d519532fe47873737ed0ac5c4c337"
  private val schemaSha256 = "a95648b5bca53f8ca07ec918de513a421ec5e4df5330aff36b08d646fdc60adf"

  test("the configured synthesis versions are synthesis-v2 and its schema v2") {
    assert(config.synthesisPromptVersion == "synthesis-v2")
    assert(config.synthesisSchemaVersion == "scholarchain.runtime.synthesis.v2")
    assert(config.synthesisPromptVersion == SynthesisAssetVersions.promptVersion)
    assert(config.synthesisSchemaVersion == SynthesisAssetVersions.schemaVersion)
  }

  test("the loaded synthesis assets carry the v2 label in prompt header, schema id and const") {
    val assets = RuntimePromptAssets.fromDirectory(prompts, config).toOption.get
    assert(assets.synthesisPrompt.startsWith("promptVersion: synthesis-v2\n"))
    assert(assets.synthesisPrompt.contains("schemaVersion: scholarchain.runtime.synthesis.v2\n"))
    assert(assets.synthesisSchema("$id").str == "scholarchain.runtime.synthesis.v2")
    assert(
      assets.synthesisSchema("properties")("schemaVersion")("const").str ==
        "scholarchain.runtime.synthesis.v2"
    )
  }

  test("the v1 files are gone and no checked-in synthesis asset still claims the v1 label") {
    assert(!Files.exists(prompts.resolve("runtime/synthesis-v1.md")))
    assert(!Files.exists(prompts.resolve("schemas/answer-synthesis-v1.json")))
    val claimsV1 = Vector("runtime/synthesis-v2.md", "schemas/answer-synthesis-v2.json").filter(f =>
      Files.readString(prompts.resolve(f)).contains("synthesis-v1") ||
        Files.readString(prompts.resolve(f)).contains("runtime.synthesis.v1")
    )
    assert(claimsV1.isEmpty)
  }

  test("a configuration that still pins synthesis-v1 is refused, not served from v2 files") {
    val oldPrompt = config.copy(synthesisPromptVersion = "synthesis-v1")
    val oldSchema = config.copy(synthesisSchemaVersion = "scholarchain.runtime.synthesis.v1")
    val both = oldPrompt.copy(synthesisSchemaVersion = "scholarchain.runtime.synthesis.v1")
    Vector(oldPrompt, oldSchema, both).foreach { c =>
      assert(
        RuntimePromptAssets.fromDirectory(prompts, c) ==
          Left(RuntimePromptAssets.RetiredSynthesisVersion)
      )
    }
  }

  test("an unknown or mixed synthesis label is a version mismatch") {
    // Built from the registry values so the result does not depend on the core configuration.
    val v2 = config.copy(
      synthesisPromptVersion = SynthesisAssetVersions.promptVersion,
      synthesisSchemaVersion = SynthesisAssetVersions.schemaVersion
    )
    Vector(
      v2.copy(synthesisPromptVersion = "synthesis-v3"),
      v2.copy(synthesisSchemaVersion = "scholarchain.runtime.synthesis.v3"),
      v2.copy(synthesisPromptVersion = "unknown")
    ).foreach { c =>
      assert(
        RuntimePromptAssets.fromDirectory(prompts, c) == Left(RuntimePromptAssets.VersionMismatch)
      )
    }
    assert(RuntimePromptAssets.fromDirectory(prompts, v2).isRight)
  }

  test("the v2 prompt and schema are pinned by hash; an in-place edit must bump the label") {
    assert(
      sha256("runtime/synthesis-v2.md") == promptSha256,
      "synthesis prompt changed under the synthesis-v2 label; bump the version, not the content"
    )
    assert(
      sha256("schemas/answer-synthesis-v2.json") == schemaSha256,
      "synthesis schema changed under the v2 label; bump the version, not the content"
    )
  }
}
