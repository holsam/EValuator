# Data ingestion for plot sections

loadAnalyseCSV <- function(path) {
  df <- readr::read_csv(path, show_col_types = FALSE)
  required <- c("tomogram", "label", "equiv_diameter_nm", "major_axis_diameter", "minor_axis_diameter", "aspect_ratio", "eccentricity", "membrane_volume", "lumen_volume", "surface_area", "is_enclosed", "closure_fill_ratio")
  validateColumns(df, required)
  df
}

# model output may be JSON (default) or the flattened CSV form (nested fields JSON-encoded per-cell)
loadModelResults <- function(path) {
  if (grepl("\\.json$", path)) {
    payload <- jsonlite::fromJSON(path, simplifyDataFrame = TRUE, flatten = TRUE)
    df <- payload$results
  } else {
    df <- readr::read_csv(path, show_col_types = FALSE)
    for (col in intersect(c("reliability.is_reliable", "reliability"), names(df))) {
      # nested reliability is JSON-encoded per cell in CSV mode; unpack is_reliable only
      if (col == "reliability") {
        parsed <- lapply(df$reliability, function(x) jsonlite::fromJSON(x))
        df$reliability.is_reliable <- vapply(parsed, function(x) isTRUE(x$is_reliable), logical(1))
      }
    }
  }
  required <- c("label_id", "source_file", "chosen_model", "radius", "rmse_nm")
  validateColumns(df, required)
  df
}

validateColumns <- function(df, required) {
  missing <- setdiff(required, names(df))
  if (length(missing) > 0) {
    stop(sprintf("Input missing required column(s): %s", paste(missing, collapse = ", ")))
  }
}

# Join analyse and model rows for the same vesicle
joinAnalyseModel <- function(analyse_df, model_df) {
  model_df$tomogram <- basename(model_df$source_file)
  dplyr::inner_join(
    analyse_df, model_df,
    by = c("tomogram" = "tomogram", "label" = "label_id"),
    suffix = c(".analyse", ".model")
  )
}
