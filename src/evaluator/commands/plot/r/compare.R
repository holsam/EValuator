# compare.R: plot group comparisons

# Parse positional arguments
args <- commandArgs(trailingOnly = TRUE)
output_dir <- args[1]; sheet_path <- args[2]; mode <- args[3]

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

# Load data sheets
sheet <- readr::read_tsv(sheet_path, show_col_types = FALSE)
loaded <- lapply(seq_len(nrow(sheet)), function(i) {
  row <- sheet[i, ]
  df <- loadAnalyseCSV(row$path)
  df$sample_id <- row$sample_id
  df$group <- row$group
  df
})
combined <- dplyr::bind_rows(loaded)

# Define features to plot and plot violin plot for each group
features <- c("equiv_diameter_nm", "aspect_ratio", "closure_fill_ratio", "lumen_volume")
pal <- groupPalette(combined$group)
for (feat in intersect(features, names(combined))) {
  p <- ggplot2::ggplot(combined, ggplot2::aes(x = group, y = .data[[feat]], fill = group)) +
    ggplot2::geom_violin(alpha = 0.6) + ggplot2::geom_boxplot(width = 0.1, outlier.shape = NA) +
    ggplot2::scale_fill_manual(values = pal) + evTheme() + ggplot2::theme(legend.position = "none")
  saveSVG(p, file.path(output_dir, paste0("violin_", feat, ".svg")))
}

# Create matrix for features and save PCA plot
feature_matrix <- combined[, intersect(features, names(combined))]
feature_matrix <- feature_matrix[stats::complete.cases(feature_matrix), ]
if (nrow(feature_matrix) >= 3 && ncol(feature_matrix) >= 2) {
  pca <- stats::prcomp(scale(feature_matrix))
  pca_df <- data.frame(pca$x[, 1:2], group = combined$group[stats::complete.cases(combined[, features])])
  p_pca <- ggplot2::ggplot(pca_df, ggplot2::aes(x = PC1, y = PC2, colour = group)) +
    ggplot2::geom_point(alpha = 0.7) + ggplot2::scale_colour_manual(values = pal) + evTheme()
  saveSVG(p_pca, file.path(output_dir, "pca.svg"), width = 6, height = 6)
}

# Write results to spreadsheet
writeXLSX(dplyr::summarise(dplyr::group_by(combined, group),
  n_evs = dplyr::n(),
  across(all_of(intersect(features, names(combined))), list(mean = ~mean(.x, na.rm=TRUE), median = ~median(.x, na.rm=TRUE)))),
  file.path(output_dir, "group_summary.xlsx"))
