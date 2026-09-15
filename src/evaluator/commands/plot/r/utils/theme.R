# Shared theme for plotting

evTheme <- function() {
  ggplot2::theme_minimal(base_size = 11) +
    ggplot2::theme(
      panel.grid.minor = ggplot2::element_blank(),
      legend.position = "right",
      plot.title = ggplot2::element_text(face = "bold")
    )
}

# Okabe-Ito for <=8 groups (colour-blind safe), Viridis beyond.
groupPalette <- function(groups) {
  okabe_ito <- c("#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000")
  n <- length(unique(groups))
  if (n <= length(okabe_ito)) okabe_ito[seq_len(n)] else viridisLite::viridis(n)
}
