import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

import streamlit as st
import yaml
import matplotlib.pyplot as plt
import numpy as np
from trtle.farmpy import Farm

"""
Streamlit App Development for groupC: (Various mooring orientations, with No shared anchors - Layout)
"""

# Define a function to plot the layout
def plot_layout(farm):
    N_m = 3
    plt.figure(figsize=(6, 6))
    farm.anchor_position(N_m)

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
    delta_x = delta_x_coefficient * farm.spacing_x * farm.WTG.diameter()
    delta_y = delta_y_coefficient * farm.spacing_y * farm.WTG.diameter()
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
    flow_map.plot_wake_map(levels=10, cmap='YlGnBu_r', plot_colorbar=True, plot_windturbines=False, ax=None)
    plt.axis('equal')
    plt.xlabel("horizontal [m]")
    plt.ylabel("Northing [m]")
    plt.title(f'Wake map for {wdir}° and {wsp} m/s')
    st.pyplot(plt)
    return np.round(local_wake_loss[0][0], 2)


# Streamlit app
st.title("Wind Farm Layout Visualization")

TEST_NAME = 'groupC_OPT_st'

layout_properties_file = os.path.join(os.path.dirname(__file__), "input_files", "groupC", "groupC_Design1_freecap.yaml")

VESSEL = 'VolturnUS-S'
DELTATHETA = 30.0

st.write("hello world")
st.write(f"{layout_properties_file}")
st.write(f"contains: {os.listdir(layout_properties_file)}")
# # Load initial layout properties
# with open(layout_properties_file, 'r') as file:
#     layout_properties = yaml.safe_load(file)
#
#
# farm = Farm()
# farm.create_layout(layout_type="standard",
#                    layout_properties=layout_properties,
#                    mooring_orientation="DMO_03",
#                    trtle=None,
#                    capacity_constraint=False)
# farm_properties = layout_properties["farm properties"]
# farm.complex_site()
#
# aep_without_wake, aep_with_wake, wake_effects = farm.wake_model(watch_circle=False)
#
# # User inputs for coefficients
# Sx = st.number_input(fr"$S_x$", min_value=4.0, max_value=12.0, value=farm_properties["Dspacingy"], step=0.1)
# Sy = st.number_input(fr"$S_y$", min_value=4.0, max_value=12.0, value=farm_properties["Dspacingx"], step=0.1)
# # delta_x_coefficient = st.slider('Delta X Coefficient', -1.0, 1.0, 0.0)
# # delta_y_coefficient = st.slider('Delta Y Coefficient', -1.0, 1.0, 0.0)
# alpha = st.number_input(rf'$\alpha$ (degrees)',
#                         min_value=0.0,
#                         max_value=360.0,
#                         value=float(layout_properties["farm properties"]["orientation"]))
# beta = st.number_input(rf'$\beta$ (degrees)',
#                         min_value=0.0,
#                         max_value=np.rad2deg(np.arctan2(Sy, Sx)),
#                         value=0.0)
# gamma = st.number_input(rf'$\Delta \gamma$ (degrees)',
#                         min_value=0.0,
#                         max_value=360.0,
#                         value=0.0)
#
# # Update layout based on user input
# layout_properties['farm properties']['Dspacingx'] = Sy
# layout_properties['farm properties']['Dspacingy'] = Sx
# layout_properties["farm properties"]["orientation"] = 90 - alpha
# layout_properties["farm properties"]["skew factor"] = np.tan(np.deg2rad(beta))*farm.spacing_x/farm.spacing_y
#
# # Commit changes
# # change_center(farm, delta_x_coefficient, delta_y_coefficient)
# farm, aep_with_wake, wake_effects = update_farm(layout_properties)
# change_gamma(farm, gamma)
#
# st.write(f"Turbine Count = {farm.turbine_ct}, Capacity = {15 * farm.turbine_ct} MW")
# st.write(f"AEP: {aep_with_wake:.2f} GWh")
# st.write(f"Total wake loss: {wake_effects:.2f}%")
#
# # Plot the layout
# plot_layout(farm)
#
# # User inputs for wind speed and direction
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