# distributions.R: plot distribution of EV morphometrics

# Parse positional arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]; analyse_path <- args[2]; mode <- args[3]

# Get script directory for path traversal
script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  script <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", script)))
})

# Import internal utilities
source(file.path(script_dir, "utils", "import.R"))
source(file.path(script_dir, "utils", "io.R"))
source(file.path(script_dir, "utils", "theme.R"))

# Import data
df <- loadAnalyseCSV(analyse_path)

# Define morphology features to plot
features <- c("equiv_diameter_nm", "major_axis_diameter", "minor_axis_diameter", "aspect_ratio", "eccentricity", "membrane_volume", "lumen_volume", "surface_area", "closure_fill_ratio")

# For each feature, create a plot and spreadsheet showing distribution
stats <- list()
for (feat in intersect(features, names(df))) {
  p <- ggplot2::ggplot(df, ggplot2::aes(x = .data[[feat]])) +
    ggplot2::geom_density(fill = "#56B4E9", alpha = 0.4) +
    ggplot2::geom_rug(alpha = 0.3) +
    evTheme() + ggplot2::labs(title = feat)
  saveSVG(p, file.path(output_dir, paste0(feat, "_density.svg")))
  v <- df[[feat]]
  stats[[feat]] <- data.frame(
    feature = feat, n = sum(!is.na(v)), mean = mean(v, na.rm = TRUE),
    median = median(v, na.rm = TRUE), sd = sd(v, na.rm = TRUE),
    p5 = quantile(v, 0.05, na.rm = TRUE), p95 = quantile(v, 0.95, na.rm = TRUE)
  )
}
writeXLSX(do.call(rbind, stats), file.path(output_dir, "summary_stats.xlsx"))
