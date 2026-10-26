package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.RuntimeConfig
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

/** Deliberately bounded JSON Schema subset used by the two checked-in schemas. Unknown keywords
  * fail closed rather than being silently ignored. This is not a general-purpose Schema engine.
  */
object RuntimeJsonSchema {
  private val keywords = Set(
    "$schema",
    "$id",
    "title",
    "description",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "enum",
    "const",
    "anyOf",
    "minimum",
    "maximum",
    "uniqueItems"
  )
  def validate(schema: ujson.Value, value: ujson.Value): Either[Vector[String], Unit] = {
    def knownSchema(s: ujson.Value, depth: Int): Boolean = {
      if (depth > 32) false
      else {
        val fields = s.obj
        fields.keySet.subsetOf(keywords) &&
        fields.get("properties").forall(_.obj.values.forall(knownSchema(_, depth + 1))) &&
        fields.get("items").forall(knownSchema(_, depth + 1)) &&
        fields.get("anyOf").forall(_.arr.forall(knownSchema(_, depth + 1)))
      }
    }
    def check(s: ujson.Value, v: ujson.Value, path: String, depth: Int): Vector[String] = {
      if (depth > 32) return Vector(s"$path:schema-depth")
      val fields = s.obj
      val unknown = fields.keySet.diff(keywords)
      if (unknown.nonEmpty) return Vector(s"$path:unsupported-schema-keyword")
      val alternatives = fields.get("anyOf").toVector.flatMap(_.arr)
      if (alternatives.nonEmpty && !alternatives.exists(a => check(a, v, path, depth + 1).isEmpty))
        return Vector(s"$path:anyOf")
      val expected = fields.get("type").map(_.str)
      val matches = expected.forall {
        case "object"  => v.isInstanceOf[ujson.Obj]
        case "array"   => v.isInstanceOf[ujson.Arr]
        case "string"  => v.isInstanceOf[ujson.Str]
        case "number"  => v.isInstanceOf[ujson.Num] && v.num.isFinite
        case "integer" => v.isInstanceOf[ujson.Num] && v.num.isFinite && v.num == math.rint(v.num)
        case "boolean" => v.isInstanceOf[ujson.Bool]
        case "null"    => v == ujson.Null
        case _         => false
      }
      if (!matches) return Vector(s"$path:type")
      var errors = Vector.empty[String]
      fields.get("const").foreach(c => if (v != c) errors :+= s"$path:const")
      fields.get("enum").foreach(e => if (!e.arr.contains(v)) errors :+= s"$path:enum")
      v match {
        case o: ujson.Obj =>
          val properties = fields.get("properties").map(_.obj.toMap).getOrElse(Map.empty)
          fields
            .get("required")
            .foreach(_.arr.foreach(k => if (!o.obj.contains(k.str)) errors :+= s"$path:required"))
          if (
            fields.get("additionalProperties").contains(ujson.Bool(false)) && o.obj.keySet
              .diff(properties.keySet)
              .nonEmpty
          )
            errors :+= s"$path:additionalProperties"
          o.obj.foreach((k, item) =>
            properties.get(k).foreach(p => errors ++= check(p, item, s"$path.$k", depth + 1))
          )
        case a: ujson.Arr =>
          fields.get("minItems").foreach(n => if (a.arr.size < n.num) errors :+= s"$path:minItems")
          fields.get("maxItems").foreach(n => if (a.arr.size > n.num) errors :+= s"$path:maxItems")
          if (
            fields
              .get("uniqueItems")
              .contains(ujson.Bool(true)) && a.arr.distinct.size != a.arr.size
          )
            errors :+= s"$path:uniqueItems"
          fields
            .get("items")
            .foreach(p =>
              a.arr.zipWithIndex.foreach((item, index) =>
                errors ++= check(p, item, s"$path[$index]", depth + 1)
              )
            )
        case ujson.Str(text) =>
          val length = text.codePointCount(0, text.length)
          fields.get("minLength").foreach(n => if (length < n.num) errors :+= s"$path:minLength")
          fields.get("maxLength").foreach(n => if (length > n.num) errors :+= s"$path:maxLength")
        case ujson.Num(number) =>
          fields.get("minimum").foreach(n => if (number < n.num) errors :+= s"$path:minimum")
          fields.get("maximum").foreach(n => if (number > n.num) errors :+= s"$path:maximum")
        case _ => ()
      }
      errors
    }
    try {
      if (!knownSchema(schema, 0)) return Left(Vector("unsupported-or-invalid-schema"))
      val errors = check(schema, value, "$", 0)
      if (errors.isEmpty) Right(()) else Left(errors.distinct)
    } catch { case NonFatal(_) => Left(Vector("invalid-schema-or-json")) }
  }
}

final case class RuntimePromptAssets(
    plannerPrompt: String,
    plannerSchema: ujson.Value,
    synthesisPrompt: String,
    synthesisSchema: ujson.Value
)
object RuntimePromptAssets {
  def fromDirectory(root: Path, config: RuntimeConfig): Either[String, RuntimePromptAssets] = try {
    def read(relative: String): String = {
      val file = root.resolve(relative)
      require(Files.size(file) <= config.maxInputBytes)
      Files.readString(file, UTF_8)
    }
    val planner = read("runtime/planner-v1.md")
    val synthesis = read("runtime/synthesis-v1.md")
    val plannerSchema = ujson.read(read("schemas/query-plan-v1.json"))
    val synthesisSchema = ujson.read(read("schemas/answer-synthesis-v1.json"))
    if (
      !planner.startsWith(s"promptVersion: ${config.plannerPromptVersion}\n") ||
      !synthesis.startsWith(s"promptVersion: ${config.synthesisPromptVersion}\n") ||
      plannerSchema("$id").str != config.plannerSchemaVersion ||
      synthesisSchema("$id").str != config.synthesisSchemaVersion
    ) Left("runtime-asset-version-mismatch")
    else Right(RuntimePromptAssets(planner, plannerSchema, synthesis, synthesisSchema))
  } catch { case NonFatal(_) => Left("runtime-assets-unavailable") }
}
