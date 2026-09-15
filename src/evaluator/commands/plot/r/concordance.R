# concordance.R: plot concordance between model and analyse

# Parse positional arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]; analyse_path <- args[2]; model_path <- args[3]; mode <- args[4]

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
analyse_df <- loadAnalyseCSV(analyse_path)
model_df <- loadModelResults(model_path)
joined <- joinAnalyseModel(analyse_df, model_df)
if (nrow(joined) == 0) {
  stop("No matching (tomogram, label) rows between analyse and model output — check both were run on the same labelled MRC(s).")
}
joined$model_diameter_nm <- joined$radius * 2

# Diameter concordance: model's fitted diameter vs analyse's two independent diameter estimates, with y = x reference line.
for (analyse_diam in c("equiv_diameter_nm", "major_axis_diameter")) {
  p <- ggplot2::ggplot(joined, ggplot2::aes(x = .data[[analyse_diam]], y = model_diameter_nm, colour = tomogram)) +
    ggplot2::geom_point(alpha = 0.6) +
    ggplot2::geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = "grey40") +
    evTheme() + ggplot2::theme(legend.position = "none") +
    ggplot2::labs(x = analyse_diam, y = "model_diameter_nm (2 x fitted radius)")
  saveSVG(p, file.path(output_dir, paste0("model_vs_", analyse_diam, ".svg")), width = 5, height = 5)
}

# See if model reliability tracks analyse's independent closure signal
p_reliab <- ggplot2::ggplot(joined, ggplot2::aes(x = reliability.is_reliable, y = closure_fill_ratio)) +
  ggplot2::geom_boxplot(fill = "#56B4E9") + evTheme() +
  ggplot2::labs(x = "model reliability.is_reliable", y = "analyse closure_fill_ratio")
saveSVG(p_reliab, file.path(output_dir, "reliability_vs_closure.svg"))

# RMSE of the fit vs whether analyse independently judged the EV enclosed
p_rmse <- ggplot2::ggplot(joined, ggplot2::aes(x = is_enclosed, y = rmse_nm)) +
  ggplot2::geom_boxplot(fill = "#D55E00") + evTheme() +
  ggplot2::labs(x = "analyse is_enclosed", y = "model rmse_nm")
saveSVG(p_rmse, file.path(output_dir, "fit_rmse_vs_enclosed.svg"))

conc_stats <- data.frame(
  n_matched = nrow(joined),
  n_analyse_only = nrow(analyse_df) - nrow(joined),
  n_model_only = nrow(model_df) - nrow(joined),
  pearson_equiv = cor(joined$equiv_diameter_nm, joined$model_diameter_nm, use = "complete.obs"),
  pearson_major = cor(joined$major_axis_diameter, joined$model_diameter_nm, use = "complete.obs"),
  reliable_pass_rate = mean(joined$reliability.is_reliable, na.rm = TRUE)
)
writeXLSX(conc_stats, file.path(output_dir, "concordance_stats.xlsx"))
