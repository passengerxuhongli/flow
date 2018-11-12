"""

"""
import logging
import numpy as np

# length of vehicles in the network, in meters
VEHICLE_LENGTH = 5


class KernelScenario(object):
    """

    """

    def __init__(self, kernel_api, network):
        """

        """
        self.kernel_api = kernel_api
        self.network = network

    def update(self):
        """

        :return:
        """
        raise NotImplementedError

    def close(self):
        """

        :return:
        """
        raise NotImplementedError

    ###########################################################################
    #                        State acquisition methods                        #
    ###########################################################################

    def edge_length(self, edge_id):
        """Return the length of a given edge/junction.

        Return -1001 if edge not found.
        """
        raise NotImplementedError

    def length(self):
        """Return the total length of all junctions and edges."""
        raise NotImplementedError

    def speed_limit(self, edge_id):
        """Return the speed limit of a given edge/junction.

        Return -1001 if edge not found.
        """
        raise NotImplementedError

    def max_speed(self):
        """Return the maximum achievable speed on any edge in the network."""
        raise NotImplementedError

    def num_lanes(self, edge_id):
        """Return the number of lanes of a given edge/junction.

        Return -1001 if edge not found.
        """
        raise NotImplementedError

    def get_edge_list(self):
        """Return the names of all edges in the network."""
        raise NotImplementedError

    def get_junction_list(self):
        """Return the names of all junctions in the network."""
        raise NotImplementedError

    def get_edge(self, x):  # TODO: maybe remove
        """Compute an edge and relative position from an absolute position.

        Parameters
        ----------
        x : float
            absolute position in network

        Returns
        -------
        edge position : tup
            1st element: edge name (such as bottom, right, etc.)
            2nd element: relative position on edge
        """
        raise NotImplementedError

    def get_x(self, edge, position):  # TODO: maybe remove
        """Return the absolute position on the track.

        Parameters
        ----------
        edge : str
            name of the edge
        position : float
            relative position on the edge

        Returns
        -------
        absolute_position : float
            position with respect to some global reference
        """
        raise NotImplementedError

    def next_edge(self, edge, lane):
        """Return the next edge/lane pair from the given edge/lane.

        These edges may also be internal links (junctions). Returns an empty
        list if there are no edge/lane pairs in front.
        """
        raise NotImplementedError

    def prev_edge(self, edge, lane):
        """Return the edge/lane pair right before this edge/lane.

        These edges may also be internal links (junctions). Returns an empty
        list if there are no edge/lane pairs behind.
        """
        raise NotImplementedError

    ###########################################################################
    #            Methods for generating initial vehicle positions.            #
    ###########################################################################

    def generate_starting_positions(self,
                                    initial_config,
                                    num_vehicles=None,
                                    **kwargs):
        """Generate starting positions for vehicles in the network.

        Calls all other starting position generating classes.

        Parameters
        ----------
        initial_config : flow.core.params.InitialConfig
            see flow/core/params.py
        num_vehicles : int, optional
            number of vehicles to be placed on the network. If no value is
            specified, the value is collected from the vehicles class
        kwargs : dict
            additional arguments that may be updated beyond initial
            configurations, such as modifying the starting position

        Returns
        -------
        startpositions : list of tuple (float, float)
            list of start positions [(edge0, pos0), (edge1, pos1), ...]
        startlanes : list of int
            list of start lanes
        startvel : list of float
            list of start speeds
        """
        num_vehicles = num_vehicles or self.vehicles.num_vehicles

        if initial_config.spacing == "uniform":
            startpositions, startlanes, startvel = self.gen_even_start_pos(
                initial_config, num_vehicles, **kwargs)
        elif initial_config.spacing == "random":
            startpositions, startlanes, startvel = self.gen_random_start_pos(
                initial_config, num_vehicles, **kwargs)
        elif initial_config.spacing == "custom":
            startpositions, startlanes, startvel = self.gen_custom_start_pos(
                initial_config, num_vehicles, **kwargs)
        else:
            raise ValueError('"spacing" argument in initial_config does not '
                             'contain a valid option')

        return startpositions, startlanes, startvel

    def gen_even_start_pos(self, initial_config, num_vehicles, **kwargs):
        """Generate uniformly spaced starting positions.

        If the perturbation term in initial_config is set to some positive
        value, then the start positions are perturbed from a uniformly spaced
        distribution by a gaussian whose std is equal to this perturbation
        term.

        Parameters
        ----------
        initial_config : InitialConfig type
            see flow/core/params.py
        num_vehicles : int
            number of vehicles to be placed on the network
        kwargs : dict
            extra components, usually defined during reset to overwrite initial
            config parameters

        Returns
        -------
        startpositions : list of tuple (float, float)
            list of start positions [(edge0, pos0), (edge1, pos1), ...]
        startlanes : list of int
            list of start lanes
        startvel : list of float
            list of start speeds
        """
        (x0, min_gap, bunching, lanes_distr, available_length,
         available_edges, initial_config) = \
            self._get_start_pos_util(initial_config, num_vehicles, **kwargs)

        increment = available_length / num_vehicles

        # if not all lanes are equal, then we must ensure that vehicles are in
        # two edges at the same time
        flag = False
        lanes = [self.num_lanes(edge) for edge in self.get_edge_list()]
        if any(lanes[0] != lanes[i] for i in range(1, len(lanes))):
            flag = True

        x = x0
        car_count = 0
        startpositions, startlanes = [], []

        # generate uniform starting positions
        while car_count < num_vehicles:
            # collect the position and lane number of each new vehicle
            pos = self.get_edge(x)

            # ensures that vehicles are not placed in an internal junction
            while pos[0] in dict(self.internal_edgestarts).keys():
                # find the location of the internal edge in total_edgestarts,
                # which has the edges ordered by position
                edges = [tup[0] for tup in self.total_edgestarts]
                indx_edge = next(
                    i for i, edge in enumerate(edges) if edge == pos[0])

                # take the next edge in the list, and place the car at the
                # beginning of this edge
                if indx_edge == len(edges) - 1:
                    next_edge_pos = self.total_edgestarts[0]
                else:
                    next_edge_pos = self.total_edgestarts[indx_edge + 1]

                x = next_edge_pos[1]
                pos = (next_edge_pos[0], 0)

            # ensures that you are in an acceptable edge
            while pos[0] not in available_edges:
                x = (x + self.edge_length(pos[0])) % self.length
                pos = self.get_edge(x)

            # ensure that in variable lane settings vehicles always start a
            # vehicle's length away from the start of the edge. This, however,
            # prevents the spacing to be completely uniform.
            if flag and pos[1] < VEHICLE_LENGTH:
                pos0, pos1 = pos
                pos = (pos0, VEHICLE_LENGTH)
                x += VEHICLE_LENGTH
                increment -= (VEHICLE_LENGTH * self.num_lanes(pos0)) / \
                             (num_vehicles - car_count)

            # place vehicles side-by-side in all available lanes on this edge
            for lane in range(min([self.num_lanes(pos[0]), lanes_distr])):
                car_count += 1
                startpositions.append(pos)
                startlanes.append(lane)

                if car_count == num_vehicles:
                    break

            x = (x + increment + VEHICLE_LENGTH + min_gap) % self.length

        # add a perturbation to each vehicle, while not letting the vehicle
        # leave its current edge
        if initial_config.perturbation > 0:
            for i in range(num_vehicles):
                perturb = np.random.normal(0, initial_config.perturbation)
                edge, pos = startpositions[i]
                pos = max(0, min(self.edge_length(edge), pos + perturb))
                startpositions[i] = (edge, pos)

        # all vehicles start with an initial speed of 0 m/s
        startvel = [0 for _ in range(len(startlanes))]

        return startpositions, startlanes, startvel

    def gen_random_start_pos(self, initial_config, num_vehicles, **kwargs):
        """Generate random starting positions.

        Parameters
        ----------
        initial_config : InitialConfig type
            see flow/core/params.py
        num_vehicles : int
            number of vehicles to be placed on the network
        kwargs : dict
            extra components, usually defined during reset to overwrite initial
            config parameters

        Returns
        -------
        startpositions : list of tuple (float, float)
            list of start positions [(edge0, pos0), (edge1, pos1), ...]
        startlanes : list of int
            list of start lanes
        startvel : list of float
            list of start speeds
        """
        (x0, min_gap, bunching, lanes_distr, available_length,
         available_edges, initial_config) = self._get_start_pos_util(
            initial_config, num_vehicles, **kwargs)

        # extra space a vehicle needs to cover from the start of an edge to be
        # fully in the edge and not risk having a gap with a vehicle behind it
        # that is smaller than min_gap
        efs = min_gap + VEHICLE_LENGTH  # extra front space

        for edge in available_edges:
            available_length -= efs * min([self.num_lanes(edge), lanes_distr])

        # choose random positions for each vehicle
        init_absolute_pos = \
            [random.random() * available_length
             for _ in range(num_vehicles)]

        # sort the positions of vehicles, for simplicity in using
        init_absolute_pos.sort()

        # these positions do not include the length of the vehicle, which need
        # to be added
        for i in range(num_vehicles):
            init_absolute_pos[i] += (VEHICLE_LENGTH + min_gap) * i

        decrement = 0
        edge_indx = 0
        startpositions = []
        startlanes = []
        for i in range(num_vehicles):
            edge_i = available_edges[edge_indx]
            pos_i = (init_absolute_pos[i] - decrement) % (
                    self.edge_length(edge_i) - efs)
            lane_i = int(((init_absolute_pos[i] - decrement) - pos_i) /
                         (self.edge_length(edge_i) - efs))

            pos_i += efs

            while lane_i > min([self.num_lanes(edge_i), lanes_distr]) - 1:
                decrement += min([self.num_lanes(edge_i), lanes_distr]) \
                             * (self.edge_length(edge_i) - efs)
                edge_indx += 1

                edge_i = available_edges[edge_indx]
                pos_i = (init_absolute_pos[i] - decrement) % (
                        self.edge_length(edge_i) - efs)

                lane_i = int(((init_absolute_pos[i] - decrement) - pos_i) /
                             (self.edge_length(edge_i) - efs))

                pos_i += efs

            startpositions.append((edge_i, pos_i))
            startlanes.append(lane_i)

        # all vehicles start with an initial speed of 0 m/s
        startvel = [0 for _ in range(len(startlanes))]

        return startpositions, startlanes, startvel

    def gen_custom_start_pos(self, initial_config, num_vehicles, **kwargs):
        """Generate a user defined set of starting positions.

        Parameters
        ----------
        initial_config : InitialConfig type
            see flow/core/params.py
        num_vehicles : int
            number of vehicles to be placed on the network
        kwargs : dict
            extra components, usually defined during reset to overwrite initial
            config parameters

        Returns
        -------
        startpositions : list of tuple (float, float)
            list of start positions [(edge0, pos0), (edge1, pos1), ...]
        startlanes : list of int
            list of start lanes
        startvel : list of float
            list of start speeds
        """
        raise NotImplementedError

    def _get_start_pos_util(self, initial_config, num_vehicles, **kwargs):
        """Prepare initial_config data for starting position methods.

        Performs some pre-processing to the initial_config and **kwargs terms,
        and returns the necessary values for all starting position generating
        functions.

        Parameters
        ----------
        initial_config : InitialConfig type
            see flow/core/params.py
        num_vehicles : int
            number of vehicles to be placed on the network
        kwargs : dict
            extra components, usually defined during reset to overwrite initial
            config parameters

        Returns
        -------
        x0 : float
            starting position of the first vehicle, in meters
        min_gap : float
            minimum gap between vehicles
        bunching : float
            the amount of space freed up in the network (per lane)
        lanes_distribution : int
            number of lanes the vehicles are supposed to be distributed over
        available_length : float
            total available free space for vehicle to be placed, over all lanes
            within the distributable lanes, in meters
        initial_config : InitialConfig type
            modified version of the initial_config parameter

        Raises
        ------
        ValueError
            If there is not enough space to place all vehicles in the allocated
            space in the network with the specified minimum gap.
        """
        x0 = initial_config.x0
        # changes to x0 in kwargs suggests a switch in between rollouts, and so
        # overwrites anything in initial_config
        if "x0" in kwargs:
            x0 = kwargs["x0"]

        bunching = initial_config.bunching
        # check if requested bunching value is not valid (negative)
        if bunching < 0:
            logging.warning('"bunching" cannot be negative; setting to 0')
            bunching = 0
        # changes to bunching in kwargs suggests a switch in between rollouts,
        #  and so overwrites anything in initial_config
        if "bunching" in kwargs:
            bunching = kwargs["bunching"]

        # compute the lanes distribution (adjust of edge cases)
        if initial_config.edges_distribution == "all":
            max_lane = max(
                [self.num_lanes(edge_id) for edge_id in self.get_edge_list()])
        else:
            max_lane = max([
                self.num_lanes(edge_id)
                for edge_id in initial_config.edges_distribution
            ])

        if initial_config.lanes_distribution > max_lane:
            lanes_distribution = max_lane
        elif initial_config.lanes_distribution < 1:
            logging.warning('"lanes_distribution" is too small; setting to 1')
            lanes_distribution = 1
        else:
            lanes_distribution = initial_config.lanes_distribution

        if initial_config.edges_distribution == "all":
            distribution_length = \
                sum([self.edge_length(edge_id) *
                     min([self.num_lanes(edge_id), lanes_distribution])
                     for edge_id in self.get_edge_list()])
        else:
            distribution_length = \
                sum([self.edge_length(edge_id) *
                     min([self.num_lanes(edge_id), lanes_distribution])
                     for edge_id in initial_config.edges_distribution])

        min_gap = max(0, initial_config.min_gap)

        if initial_config.edges_distribution == "all":
            available_edges = self.get_edge_list()
        else:
            available_edges = initial_config.edges_distribution

        available_length = \
            distribution_length - lanes_distribution * bunching - \
            num_vehicles * (min_gap + VEHICLE_LENGTH)

        if available_length < 0:
            raise ValueError("There is not enough space to place all vehicles "
                             "in the network.")

        return (x0, min_gap, bunching, lanes_distribution, available_length,
                available_edges, initial_config)
