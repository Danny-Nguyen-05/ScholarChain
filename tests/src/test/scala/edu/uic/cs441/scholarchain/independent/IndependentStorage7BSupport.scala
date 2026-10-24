package edu.uic.cs441.scholarchain.independent

import software.amazon.awssdk.core.document.Document

import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Offline SDK boundaries fail unexpected invocations instead of creating clients or requests. */
object IndependentStorage7BSupport {
  def stub[A](kind: Class[A])(
      handler: PartialFunction[(String, Vector[AnyRef]), AnyRef]
  ): A = kind.cast(
    Proxy.newProxyInstance(
      kind.getClassLoader,
      Array(kind),
      new InvocationHandler {
        def invoke(self: AnyRef, method: Method, args: Array[AnyRef]): AnyRef = {
          val call = method.getName -> Option(args).map(_.toVector).getOrElse(Vector.empty)
          if (handler.isDefinedAt(call)) handler(call)
          else throw new AssertionError(s"Unexpected offline SDK invocation: ${method.getName}")
        }
      }
    )
  )

  def document(json: ujson.Value): Document = json match {
    case ujson.Str(value)  => Document.fromString(value)
    case ujson.Num(value)  => Document.fromNumber(value)
    case ujson.Bool(value) => Document.fromBoolean(value)
    case ujson.Null        => Document.fromNull()
    case value: ujson.Obj =>
      Document.fromMap(value.obj.iterator.map((k, v) => k -> document(v)).toMap.asJava)
    case value: ujson.Arr => Document.fromList(value.arr.map(document).asJava)
  }

  def temporary[A](label: String)(body: Path => A): A = {
    val root = Files.createTempDirectory(label)
    try body(root)
    finally {
      val walk = Files.walk(root)
      try
        walk
          .sorted(java.util.Comparator.reverseOrder[Path]())
          .iterator()
          .asScala
          .foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }
}
