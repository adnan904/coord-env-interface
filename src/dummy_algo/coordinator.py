import argparse
from collections import defaultdict
import logging
import os
from random import uniform
from spinterface import SimulatorAction
from common.common_functionaliies import round_off_list_to_1

# select which simulator to use by (un-)commenting the corresponding imports
# from dummy_env import DummySimulator as Simulator
# for use with the flow-level simulator https://github.com/RealVNF/coordination-simulation (after installation)
from siminterface.simulator import Simulator

log = logging.getLogger(__name__)


# The dummy-coordinator places each sf in each node of the network
def get_placement(nodes_list, sf_list):
    placement = defaultdict(list)
    for node in nodes_list:
        placement[node] = sf_list
    return placement


'''
    Schedule is of the following form:
        schedule : dict
            {
                'node id' : dict
                {
                    'SFC id' : dict
                    {
                        'SF id' : dict
                        {
                            'node id' : float (Inclusive of zero values)
                        }
                    }
                }
            }
'''


# for each node in the network, we generate floating point random numbers in the range 0 to 1
# we divide each of these numbers by the sum of all of these numbers, so that Prob. Distribution = 1
def get_schedule(nodes_list, sf_list, sfc_list):
    schedule = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    for outer_node in nodes_list:
        for sfc in sfc_list:
            for sf in sf_list:
                # this list may not sum to 1
                random_prob_list = [uniform(0, 1) for _ in range(len(nodes_list))]
                sum_prob = sum(random_prob_list)
                # prob list with sum of all prob. equal to 1
                prob_list = [round(prob / sum_prob, 2) for prob in random_prob_list]
                # Because of floating point precision (.59 + .33 + .08) can be equal to .99999999
                # So we correct the sum only if the absolute difference is more than a tolerance(0.0000152587890625)
                if abs(1.0 - sum(prob_list)) > 1 / 2 ** 16:
                    prob_list = round_off_list_to_1(prob_list)
                assert abs(1.0 - sum(prob_list)) < 1 / 2 ** 16, "Sum of random probabilities not equal to 1.0"
                for inner_node in nodes_list:
                    if len(prob_list) != 0:
                        schedule[outer_node][sfc][sf][inner_node] = prob_list.pop()
                    else:
                        schedule[outer_node][sfc][sf][inner_node] = 0
    return schedule


def parse_args():
    parser = argparse.ArgumentParser(description="Dummy Coordinator")
    parser.add_argument('-i', '--iterations', required=False, default=10, dest="iterations", type=int)
    parser.add_argument('-s', '--seed', required=False, default=9999, dest="seed", type=int)
    parser.add_argument('-n', '--network', required=True, dest='network')
    parser.add_argument('-sf', '--service_functions', required=True, dest="service_functions")
    parser.add_argument('-c', '--config', required=True, dest="config")
    return parser.parse_args()


def main():
    # Parse arguments
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("coordsim").setLevel(logging.WARNING)
    # creating the simulator
    simulator = Simulator()
    init_state = simulator.init(os.path.abspath(args.network),
                                os.path.abspath(args.service_functions),
                                os.path.abspath(args.config), args.seed)
    log.info("Network Stats after init(): %s", init_state.network_stats)
    nodes_list = [node['id'] for node in init_state.network.get('nodes')]
    sf_list = list(init_state.service_functions.keys())
    sfc_list = list(init_state.sfcs.keys())
    # we place every sf in each node of the network, so placement is calculated only once
    placement = get_placement(nodes_list, sf_list)
    # iterations define the number of time we wanna call apply()
    for i in range(args.iterations):
        schedule = get_schedule(nodes_list, sf_list, sfc_list)
        action = SimulatorAction(placement, schedule)
        apply_state = simulator.apply(action)
        log.info("Network Stats after apply() # %s: %s", i + 1, apply_state.network_stats)


if __name__ == '__main__':
    main()
