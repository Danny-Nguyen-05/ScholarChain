import java.util.Map;
import java.util.TreeMap;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SparkSession;

/** Bounded local evidence probe for the 28-row Phase 6C smoke counter table. */
public final class CounterInspect {
  public static void main(String[] args) {
    if (args.length != 1) throw new IllegalArgumentException("expected counters Parquet path");
    SparkSession spark = SparkSession.builder()
        .appName("Phase6C repair counter evidence")
        .master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate();
    try {
      Dataset<Row> counters = spark.read().parquet(args[0]);
      Map<String, Long> observed = new TreeMap<>();
      for (Row row : counters.select("name", "value").collectAsList()) {
        observed.put(row.getString(0), row.getLong(1));
      }
      Map<String, Long> expected = Map.of(
          "erResearcherUnresolved", 6L,
          "erResearcherConflicts", 0L,
          "erWorkUnresolved", 0L,
          "erWorkConflicts", 3L,
          "missingGraphEndpoints", 0L);
      expected.forEach((name, value) -> {
        System.out.println(name + "=" + observed.get(name));
        if (!value.equals(observed.get(name))) {
          throw new AssertionError(name + " expected " + value + " but saw " + observed.get(name));
        }
      });
      System.out.println("totalCounterNames=" + observed.size());
    } finally {
      spark.stop();
    }
  }
}
