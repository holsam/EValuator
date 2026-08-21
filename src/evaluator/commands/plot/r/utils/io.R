# Shared utilities for input/output operations

# Save a plot to SVG file
saveSVG <- function(plot, path, width = 6, height = 4) {
  ggplot2::ggsave(path, plot = plot, width = width, height = height, device = "svg")
}

# Save a dataframe to a XLSX spreadsheet
writeXLSX <- function(df, path, sheet = "Sheet1") {
  openxlsx::write.xlsx(df, path, sheetName = sheet, overwrite = TRUE)
}