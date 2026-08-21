# Shared utilities for input/output operations

# Save a plot to SVG file
saveSVG <- function(plot, path, width = 6, height = 4) {
  ggplot2::ggsave(path, plot = plot, width = width, height = height, device = "svg")
}

# Save a dataframe to a XLSX spreadsheet
writeXLSX <- function(df, path, sheet = "Sheet1") {
  openxlsx::write.xlsx(df, path, sheetName = sheet, overwrite = TRUE)
  stripDanglingDrawingRefs(path)
}

# stripDanglingDrawingRefs: fix a bug in openxlsx (>= 4.2.8) where worksheet entries aren't included in zip file causing issue with some readers
stripDanglingDrawingRefs <- function(path) {
  tmp <- tempfile()
  dir.create(tmp)
  on.exit(unlink(tmp, recursive = TRUE), add = TRUE)
  zip::unzip(path, exdir = tmp)

  relsPath <- file.path(tmp, "xl", "worksheets", "_rels", "sheet1.xml.rels")
  if (file.exists(relsPath)) {
    s <- readLines(relsPath, warn = FALSE)
    s <- gsub('<Relationship[^>]*Type="[^"]*(drawing|vmlDrawing)[^"]*"[^>]*/>', "", s)
    writeLines(s, relsPath)
  }

  ctPath <- file.path(tmp, "[Content_Types].xml")
  if (file.exists(ctPath)) {
    s <- readLines(ctPath, warn = FALSE)
    s <- gsub('<Override[^>]*PartName="/xl/drawings/drawing1.xml"[^>]*/>', "", s)
    writeLines(s, ctPath)
  }

  files <- list.files(tmp, recursive = TRUE, all.files = TRUE)
  unlink(path)
  old <- setwd(tmp)
  on.exit(setwd(old), add = TRUE)
  zip::zip(path, files)
}