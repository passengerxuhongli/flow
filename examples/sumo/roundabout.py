"""Example of a figure 8 network with human-driven vehicles.

Right-of-way dynamics near the intersection causes vehicles to queue up on
either side of the intersection, leading to a significant reduction in the
average speed of vehicles in the network.
"""
from flow.controllers import IDMController, StaticLaneChanger, ContinuousRouter
from flow.core.experiment import SumoExperiment
from flow.core.params import SumoParams, EnvParams, NetParams
from flow.core.vehicles import Vehicles
from flow.envs.loop.loop_accel import AccelEnv, ADDITIONAL_ENV_PARAMS
from flow.scenarios.roundabout.scenario import RoundAboutScenario, \
    ADDITIONAL_NET_PARAMS
from flow.scenarios.roundabout.gen import RoundAboutGenerator


def round_about_example(render=None):
    """
    Perform a simulation of vehicles on a roundabout.

    Parameters
    ----------
    render: bool, optional
        specifies whether to use sumo's gui during execution

    Returns
    -------
    exp: flow.core.SumoExperiment type
        A non-rl experiment demonstrating the performance of human-driven
        vehicles on a roundabout.
    """
    sumo_params = SumoParams(render=True)

    if render is not None:
        sumo_params.render = render

    vehicles = Vehicles()
    vehicles.add(
        veh_id="idm",
        acceleration_controller=(IDMController, {}),
        lane_change_controller=(StaticLaneChanger, {}),
        routing_controller=(ContinuousRouter, {}),
        speed_mode="no_collide",
        initial_speed=0,
        num_vehicles=1)

    env_params = EnvParams(additional_params=ADDITIONAL_ENV_PARAMS)

    additional_net_params = ADDITIONAL_NET_PARAMS.copy()
    net_params = NetParams(
        no_internal_links=False, additional_params=additional_net_params)

    scenario = RoundAboutScenario(
        name="roundabout",
        generator_class=RoundAboutGenerator,
        vehicles=vehicles,
        net_params=net_params)

    env = AccelEnv(env_params, sumo_params, scenario)

    return SumoExperiment(env, scenario)


if __name__ == "__main__":
    # import the experiment variable
    exp = round_about_example()

    # run for a set number of rollouts / time steps
    exp.run(1, 1500)