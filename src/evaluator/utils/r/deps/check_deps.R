# check_deps.R: report which R dependencies are installed (as JSON to stdout)

script_dir <- local({
  args <- commandArgs(trailingOnly = FALSE)
  script <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", script)))
})
source(file.path(script_dir, "dependencies.R"))

all_packages <- c(R_DEPENDENCIES$cran)
installed <- character(0)
missing <- character(0)
for (pkg in all_packages) {
  ok <- tryCatch(requireNamespace(pkg, quietly = TRUE), error = function(e) FALSE)
  if (ok) installed <- c(installed, pkg) else missing <- c(missing, pkg)
}
cat(sprintf(
  '{"installed":[%s],"missing":[%s]}',
  paste(sprintf('"%s"', installed), collapse = ","),
  paste(sprintf('"%s"', missing), collapse = ",")
))
