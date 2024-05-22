import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

import streamlit as st
import yaml
import matplotlib.pyplot as plt
import numpy as np
from trtle.farmpy import Farm

"""
Streamlit App Development for groupC: (Various mooring orientations, with No shared anchors) - Powered by TRTLE: https://github.com/Yuksel-Rudy/TRTLE
"""

# Define a function to plot the layout
def plot_layout(farm):
    N_m = 3
    plt.figure(figsize=(6, 6))
    for i, turbine in enumerate(farm.turbines.values()):
        for j in range(N_m):
            plt.plot([turbine[f"anchor{j}_x"], turbine["x"]], [turbine[f"anchor{j}_y"], turbine["y"]], '-', color='black', linewidth=1.0)

    plt.gca().set_axisbelow(True)
    plt.axis("equal")
    plt.plot(farm.oboundary_x, farm.oboundary_y, label="farm boundary")
    plt.xlabel("Easting [m]")
    plt.ylabel("Northing [m]")

    for idx, (x, y) in enumerate(zip(farm.layout_x, farm.layout_y)):
        plt.text(x, y, f' {idx}', color='red', verticalalignment='bottom', horizontalalignment='right')

    st.pyplot(plt)


def update_farm(layout_properties):
    farm = Farm()
    farm.create_layout(layout_type="standard",
                       layout_properties=layout_properties,
                       mooring_orientation="DMO_03",
                       trtle=None,
                       capacity_constraint=False)
    farm.complex_site()
    aep_without_wake, aep_with_wake, wake_effects = farm.wake_model(watch_circle=False)
    return farm, aep_with_wake, wake_effects


def change_center(farm, delta_x_coefficient, delta_y_coefficient):
    delta_x = delta_x_coefficient * farm.WTG.diameter()
    delta_y = delta_y_coefficient * farm.WTG.diameter()
    for i, turbine in enumerate(farm.turbines.values()):
        new_x = turbine["x"] + delta_x
        new_y = turbine["y"] + delta_y
        farm.add_update_turbine_keys(i, "x", new_x)
        farm.add_update_turbine_keys(i, "y", new_y)


def change_gamma(farm, gamma):
    for i, turbine in enumerate(farm.turbines.values()):
        farm.add_update_turbine_keys(i, "mori", turbine["mori"] - gamma)


def plot_wake_map(farm, wdir, wsp):
    flow_map = farm.sim_res.flow_map(grid=None, wd=wdir, ws=wsp)
    wdir_idx = np.isin(farm.sim_res.wd.values, wdir)
    wsp_idx = np.isin(farm.sim_res.ws.values, wsp)
    with_wake = farm.sim_res.aep(with_wake_loss=True).sum(axis=0)[wdir_idx, wsp_idx].values
    without_wake = farm.sim_res.aep(with_wake_loss=False).sum(axis=0)[wdir_idx, wsp_idx].values
    local_wake_loss = np.abs(with_wake - without_wake)/without_wake * 1e2

    plt.figure()
    flow_map.plot_wake_map(levels=5, cmap='YlGnBu_r', plot_colorbar=True, plot_windturbines=False, ax=None)
    plt.axis('equal')
    plt.xlabel("horizontal [m]")
    plt.ylabel("Northing [m]")
    plt.title(f'Wake map for {wdir}° and {wsp} m/s')
    st.pyplot(plt)
    return np.round(local_wake_loss[0][0], 2)


# Streamlit app
st.title("IEA Task 49 - Wind Farm Layout Design & Visualization")

TEST_NAME = 'groupC_OPT_st'

layout_properties_file = os.path.join(os.path.dirname(__file__), "input_files", "groupC", "GroupC_Design1_freecap.yaml")

VESSEL = 'VolturnUS-S'
DELTATHETA = 30.0

# Load initial layout properties
with open(layout_properties_file, 'r') as file:
    layout_properties = yaml.safe_load(file)


farm = Farm()
farm.create_layout(layout_type="standard",
                   layout_properties=layout_properties,
                   mooring_orientation="DMO_03",
                   trtle=None,
                   capacity_constraint=False)
farm_properties = layout_properties["farm properties"]
farm.complex_site()

aep_without_wake, aep_with_wake, wake_effects = farm.wake_model(watch_circle=False)

# User inputs for coefficients

# Create two columns
col1, col2, col3 = st.columns(3)


with col1:
    Sx = st.number_input(fr"$S_x = D_x/D$: Spacing in x-axis (-)", min_value=4.0, max_value=12.0, value=farm_properties["Dspacingy"], step=0.1)
    Sy = st.number_input(fr"$S_y = D_y/D$: Spacing in y-axis (-)", min_value=4.0, max_value=12.0,
                         value=farm_properties["Dspacingx"], step=0.1)
    delta_x_coefficient = st.slider(fr'$\Delta x/D$: center adjustment in x-axis [-]', -10.0, 10.0, 0.0)
    delta_y_coefficient = st.slider(fr'$\Delta y/D$: center adjustment in y-axis [-]', -10.0, 10.0, 0.0)
with col2:
    alpha = st.number_input(rf'$\alpha$: farm orientation angle (degrees)',
                            min_value=0.0,
                            max_value=360.0,
                            value=float(layout_properties["farm properties"]["orientation"]))
    beta = st.number_input(rf'$\beta$: skew angle (degrees)',
                           min_value=0.0,
                           max_value=np.rad2deg(np.arctan2(Sy, Sx)),
                           value=0.0)
    gamma = st.number_input(rf'$\Delta \gamma$: delta heading angle (degrees)',
                            min_value=0.0,
                            max_value=360.0,
                            value=0.0)

with col3:
    msr = st.number_input(fr"$R_a$: anchor radius (m)", min_value=0.0, max_value=1400.0,
                          value=float(farm_properties["mooring line spread radius"]), step=1.0)
    tbl = st.number_input(fr"$R_b$: turbine-boundary limit (m)", min_value=0.0, max_value=1400.0,
                          value=float(farm_properties["turbine-boundary limit"]), step=1.0)
# Update layout based on user input
layout_properties['farm properties']['Dspacingx'] = Sy
layout_properties['farm properties']['Dspacingy'] = Sx
layout_properties["farm properties"]["orientation"] = 90 - alpha
layout_properties["farm properties"]["skew factor"] = np.tan(np.deg2rad(beta))*farm.spacing_x/farm.spacing_y
layout_properties["farm properties"]["mooring line spread radius"] = msr
layout_properties["farm properties"]["turbine-boundary limit"] = tbl

# Commit changes
farm, aep_with_wake, wake_effects = update_farm(layout_properties)
change_center(farm, delta_x_coefficient, delta_y_coefficient)
change_gamma(farm, gamma)





# Plot the layout
plot_layout(farm)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.write(f"**Turbine Count** = {farm.turbine_ct}")
with col2:
    st.write(f"**Capacity** = {15 * farm.turbine_ct} MW")
with col3:
    st.write(f"**AEP**: {aep_with_wake:.2f} GWh")
with col4:
    st.write(f"**Total wake loss**: {wake_effects:.2f}%")

# User inputs for wind speed and direction
# wsp = st.slider('Wind Speed (m/s)',
#                 min_value=3.0,
#                 max_value=25.0,
#                 value=11.0,
#                 step=farm.site.ds.ws.__array__()[1] - farm.site.ds.ws.__array__()[0])
# wdir = st.slider('Wind Direction (degrees)',
#                  min_value=0.0,
#                  max_value=360.0,
#                  value=0.0,
#                  step=farm.site.ds.wd.__array__()[1] - farm.site.ds.wd.__array__()[0])
# local_wake_loss = plot_wake_map(farm, wdir, wsp)
# st.write(f"local wake effect = {local_wake_loss}%")