# qc.R: plot qc metrics

# Parse positional arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]; analyse_path <- args[2]; mode <- args[3]; fill_ratio_flag_threshold <- as.numeric(args[4])

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

# Calculate number of EVs per tomogram and plot
count_per_tomo <- dplyr::count(df, tomogram, name = "n_evs")
saveSVG(ggplot2::ggplot(count_per_tomo, ggplot2::aes(x = tomogram, y = n_evs)) +
  ggplot2::geom_col(fill = "#0072B2") + evTheme() +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1)),
  file.path(output_dir, "count_per_tomogram.svg"))

# Calculate number of enclosed EVs per tomogram and plot
pass_rate <- dplyr::summarise(dplyr::group_by(df, tomogram),
  pass_rate = mean(is_enclosed, na.rm = TRUE), .groups = "drop")
saveSVG(ggplot2::ggplot(pass_rate, ggplot2::aes(x = tomogram, y = pass_rate)) +
  ggplot2::geom_col(fill = "#009E73") + ggplot2::ylim(0, 1) + evTheme() +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1)),
  file.path(output_dir, "closure_pass_rate.svg"))

saveSVG(ggplot2::ggplot(df, ggplot2::aes(x = closure_fill_ratio)) +
  ggplot2::geom_histogram(bins = 30, fill = "#D55E00") + evTheme() +
  ggplot2::geom_vline(xintercept = fill_ratio_flag_threshold, linetype = "dashed", colour = "black"),
  file.path(output_dir, "closure_fill_ratio_distribution.svg"))

writeXLSX(dplyr::summarise(dplyr::group_by(df, tomogram),
  n_evs = dplyr::n(), pass_rate = mean(is_enclosed, na.rm = TRUE),
  median_fill_ratio = median(closure_fill_ratio, na.rm = TRUE),
  n_flagged_low_fill = sum(closure_fill_ratio < fill_ratio_flag_threshold, na.rm = TRUE),
  .groups = "drop"),
  file.path(output_dir, "qc_summary.xlsx"))
