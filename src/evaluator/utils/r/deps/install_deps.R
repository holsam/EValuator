# install_deps.R: install R dependencies for evaluator plot command (only installing missing packages)

script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  script <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", script)))
})
source(file.path(script_dir, "dependencies.R"))

is_missing <- function(pkg) !requireNamespace(pkg, quietly = TRUE)

missing_cran <- Filter(is_missing, R_DEPENDENCIES$cran)

if (length(missing_cran) == 0) {
  message("All R report dependencies are already installed.")
  quit(status = 0)
}

if (length(missing_cran) > 0) {
  message(sprintf("Installing %d CRAN package(s): %s", length(missing_cran), paste(missing_cran, collapse = ", ")))
  install.packages(missing_cran, repos = "https://cloud.r-project.org")
}

still_missing <- Filter(is_missing, c(R_DEPENDENCIES$cran, R_DEPENDENCIES$bioc))
if (length(still_missing) > 0) {
  message(sprintf("Still missing after install attempt: %s", paste(still_missing, collapse = ", ")))
  quit(status = 1)
}

message("All R report dependencies installed successfully.")