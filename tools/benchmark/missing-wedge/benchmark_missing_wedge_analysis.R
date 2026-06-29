setwd("~/Documents/dev/projects/EValuator")

library(tidyverse)

# Data pre-processing -----------------------------------------------------
# Open error data
data <- read_csv(file='benchmark_missing_wedge_err.csv') %>%
  distinct()
# identify metadata columns
metadata_cols <- c(
  "nominal_diameter_nm",
  "true_diameter_nm",
  "replicate"
)
# tidy up data
data_tidy <- data %>%
  select(-c(
    fit_rmse_nm,
    z_extent_nm,
    xy_z_ratio,
    orientation_score,
    anisotropy,
    )) %>%
  rename(
    "convex_hull_d_nm"="hull_d_nm",
    "convex_hull_relative_error"="convex hull_relative_error",
    "convex_hull_error"="convex hull_error",
    "xy_relative_error"="XY-projection diameter_relative_error",
    "xy_error"="XY-projection diameter_error",
    # "closed_relative_error"="anisotropic closing_relative_error",
    # "closed_error"="anisotropic closing_error",
    "fit_relative_error"="sphere fit_relative_error",
    "fit_error"="sphere fit_error",
  ) %>%
  filter(nominal_diameter_nm > 0)

# pivot data to long format
data_long <- data_tidy %>%
  pivot_longer(
    cols = -all_of(metadata_cols),
    names_to = "name",
    values_to = "value"
  ) %>%
  group_by(true_diameter_nm, replicate) %>%
  mutate(id=cur_group_id(), .before="true_diameter_nm") %>%
  ungroup() %>%
  mutate(
    # classify measurement type
    measure = case_when(
      str_detect(name, "_d_nm$") ~ "diameter",
      str_detect(name, "_relative_error$") ~ "relative_error",
      str_detect(name, "_error$") ~ "error",
      TRUE ~ NA_character_
    ),
    # extract mitigation name
    mitigation = name %>%
      str_remove("_d_nm$") %>%
      str_remove("_relative_error$") %>%
      str_remove("_error$")
  ) %>%
  select(-name) %>%
  pivot_wider(
    names_from = measure,
    values_from = value
  ) %>%
  select(id, all_of(metadata_cols), mitigation, diameter, error, relative_error) %>%
  mutate(
    Mitigation = case_when(
      str_detect(mitigation, "baseline") ~ "No mitigation applied",
      str_detect(mitigation, "convex_hull") ~ "Calculated from convex hull",
      str_detect(mitigation, "fit") ~ "Calculated from least-squares fit model",
      str_detect(mitigation, "xy") ~ "Calculated from maximum x-y area",
    )
  )

data_long$Mitigation <- as.factor(factor(data_long$Mitigation, levels=c("No mitigation applied", "Calculated from convex hull", "Calculated from least-squares fit model", "Calculated from maximum x-y area")))



data_abs <- data_long %>%
  mutate(
    abs_err = abs(error),
    abs_rel_err = abs(relative_error)
  )


# Visualisations ----------------------------------------------------------
# Plot relative error vs true diameter
data_long %>%
  filter(mitigation != "lumen") %>%
  filter(mitigation != "closed") %>%
  ggplot(aes(x=true_diameter_nm, y=relative_error, shape=Mitigation, col=Mitigation)) +
  theme_bw() +
  geom_point(alpha=0.6)+
  geom_smooth(method=lm) +
  labs(x="True Diameter (nm)", y="Relative error of calculated diameter")

# Plot diameter vs true diameter
data_long %>%
  filter(mitigation != "lumen") %>%
  filter(mitigation != "closed") %>%
  ggplot(aes(x=true_diameter_nm, y=diameter/true_diameter_nm, shape=Mitigation, col=Mitigation)) +
  theme_bw() +
  geom_point(alpha=0.6)+
  geom_smooth(method=lm) +
  labs(x="True Diameter (nm)", y="Ratio of calculated diameter / true diameter")

