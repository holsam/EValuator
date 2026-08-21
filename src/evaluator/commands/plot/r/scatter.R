# scatter.R: plot scatter graph of morphometrics

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

# Define list of pairs to analyse
pairs <- list(
  c("equiv_diameter_nm", "lumen_volume"),
  c("surface_area", "lumen_volume"),
  c("aspect_ratio", "equiv_diameter_nm")
)
stats_rows <- list()

# For each pair, plot the scatter and write a spreadsheet with stats
for (pair in pairs) {
  x <- pair[1]; y <- pair[2]
  p <- ggplot2::ggplot(df, ggplot2::aes(x = .data[[x]], y = .data[[y]], colour = tomogram)) +
    ggplot2::geom_point(alpha = 0.6) +
    ggplot2::geom_smooth(method = "lm", se = FALSE, linewidth = 0.5) +
    evTheme() + ggplot2::theme(legend.position = "none")
  saveSVG(p, file.path(output_dir, paste0(x, "_vs_", y, ".svg")))
  fit <- lm(df[[y]] ~ df[[x]])
  stats_rows[[length(stats_rows) + 1]] <- data.frame(
    x = x, y = y,
    pearson_r = cor(df[[x]], df[[y]], use = "complete.obs"),
    spearman_r = cor(df[[x]], df[[y]], use = "complete.obs", method = "spearman"),
    slope = coef(fit)[2], slope_se = summary(fit)$coefficients[2, 2]
  )
}
writeXLSX(do.call(rbind, stats_rows), file.path(output_dir, "scatter_stats.xlsx"))
