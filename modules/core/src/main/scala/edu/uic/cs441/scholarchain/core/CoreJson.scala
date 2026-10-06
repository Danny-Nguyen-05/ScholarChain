package edu.uic.cs441.scholarchain.core

import upickle.default.{ReadWriter, read, write}

object CoreJson {
  def compact[T: ReadWriter](value: T): String = write(value)

  def pretty[T: ReadWriter](value: T): String = write(value, indent = 2)

  def parse[T: ReadWriter](json: String): Either[DomainViolation, T] =
    try Right(read[T](json))
    catch {
      case error: Throwable =>
        Left(
          DomainViolation(
            ViolationCode.MalformedInput,
            Option(error.getMessage).getOrElse(error.getClass.getName)
          )
        )
    }

  def parseAndValidate[T: ReadWriter](
      json: String
  )(validate: T => Either[Vector[DomainViolation], T]): Either[Vector[DomainViolation], T] =
    parse(json) match {
      case Left(violation) => Left(Vector(violation))
      case Right(value)    => validate(value)
    }
}
