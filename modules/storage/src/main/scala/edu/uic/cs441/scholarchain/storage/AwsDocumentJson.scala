package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.core.document.Document
import scala.jdk.CollectionConverters.*

/** Lossless structural JSON value: numbers remain decimals, not Double or quoted strings. */
private[storage] enum AwsJson {
  case ObjectValue(fields: Map[String, AwsJson])
  case ArrayValue(items: Vector[AwsJson])
  case StringValue(text: String)
  case NumberValue(decimal: java.math.BigDecimal)
  case BooleanValue(boolean: Boolean)
  case NullValue
  def obj: Map[String, AwsJson] = this match {
    case ObjectValue(v) => v; case _ => throw new IllegalArgumentException("expected JSON object")
  }
  def arr: Vector[AwsJson] = this match {
    case ArrayValue(v) => v; case _ => throw new IllegalArgumentException("expected JSON array")
  }
  def str: String = this match {
    case StringValue(v) => v; case _ => throw new IllegalArgumentException("expected JSON string")
  }
  def apply(key: String): AwsJson = obj(key)
  def apply(index: Int): AwsJson = arr(index)

  /** String escaping uses the JSON library, while numeric rendering keeps the exact decimal. */
  def render: String = this match {
    case ObjectValue(fields) =>
      fields.toVector
        .sortBy(_._1)
        .map((k, v) => ujson.Str(k).render() + ":" + v.render)
        .mkString("{", ",", "}")
    case ArrayValue(items)     => items.map(_.render).mkString("[", ",", "]")
    case StringValue(text)     => ujson.Str(text).render()
    case NumberValue(decimal)  => decimal.toString
    case BooleanValue(boolean) => if (boolean) "true" else "false"
    case NullValue             => "null"
  }
}

/** Never interprets the SDK's diagnostic toString representation as JSON. */
private[storage] object AwsDocumentJson {
  def value(document: Document): AwsJson = {
    if (document == null || document.isNull) AwsJson.NullValue
    else if (document.isString) AwsJson.StringValue(document.asString())
    else if (document.isBoolean) AwsJson.BooleanValue(document.asBoolean())
    else if (document.isMap)
      AwsJson.ObjectValue(
        document.asMap().asScala.iterator.map((key, item) => key -> value(item)).toMap
      )
    else if (document.isList)
      AwsJson.ArrayValue(document.asList().asScala.iterator.map(value).toVector)
    else if (document.isNumber) AwsJson.NumberValue(document.asNumber().bigDecimalValue())
    else throw new IllegalArgumentException("unsupported AWS document kind")
  }
}
