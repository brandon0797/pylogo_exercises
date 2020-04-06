
from __future__ import annotations

from random import choice, randint, sample
from typing import Any, List, NewType, Tuple

from core.sim_engine import SimEngine
from core.world_patch_block import World


Gene = NewType('Gene', Any)
Chromosome = NewType('Chromosome', Tuple[Gene])


class Individual:
    """
    Note: An individual is NOT an agent. Individual is a separate, stand-alone class.

    An individual is a sequence of chromosome. The chromosome are typically all of the same type, e.g.,
    a integer, a pixel, etc. The sequence is stored as a tuple to ensure that it is immutable.

    In loop.py points on the screen, i.e., Pixel_xy objects, are the chromosome. As far as PyLogo is
    concerned, they are agents. They serve as chromosome in individuals.
    """

    def __init__(self, chromosome: Chromosome):
        self.chromosome: Chromosome = chromosome
        # No need to compute fitness multiple times. Cache it here.
        self.fitness = self.compute_fitness()

    def compute_fitness(self):
        pass

    @staticmethod
    def cx_all_diff(ind_1, ind_2) -> Tuple[Individual, Individual]:
        """
        Perform crossover between self and other while preserving all_different.
        """
        child_1 = GA_World.individual_class(Individual.cx_all_diff_chromosome(ind_1.chromosome, ind_2.chromosome))
        child_2 = GA_World.individual_class(Individual.cx_all_diff_chromosome(ind_2.chromosome, ind_1.chromosome))
        return (child_1, child_2)

    @staticmethod
    def cx_all_diff_chromosome(chromosome_1: Chromosome, chromosome_2: Chromosome) -> Chromosome:
        """
        chromosome_1 and chromosome_2 are the same length

        Returns: a selection from chromosome_1 and chromosome_2 preserving all_different
        """
        # This ensures that the rotations are non-trivial.
        inner_indices = range(1, len(chromosome_1)-1) if len(chromosome_1) > 2 else range(len(chromosome_1))
        chromosome_1_rotated = Individual.rotate_by(chromosome_1, choice(inner_indices))
        chromosome_2_rotated = Individual.rotate_by(chromosome_2, choice(inner_indices))
        indx = choice(inner_indices)

        child_chromosome = chromosome_1_rotated[: indx] + \
                         [Gene for Gene in chromosome_2_rotated if Gene not in chromosome_1_rotated[: indx]]
        return child_chromosome[:len(chromosome_1)]

    @property
    def discrepancy(self):
        discr = abs(round(self.fitness - GA_World.fitness_target, 1))
        return discr

    def mate_with(self, other) -> Tuple[Individual, Individual]:
        pass

    def mutate(self) -> Individual:
        pass

    @staticmethod
    def move_elt(chromosome: Chromosome):
        """
        This is our own mutation operator. It moves an Gene from one place to another in the list.
        """
        # Ensures that the two index positions are different.
        (indx_1, indx_2) = sample(list(range(len(chromosome))), 2)
        # Can't perform the next line on a tuple. So change it into
        # a list and then change it back into a tuple. That way the
        # original tuple is unchanged.
        list_chromosome: List[Any] = list(chromosome)
        list_chromosome.insert(indx_2, list_chromosome.pop(indx_1))
        return tuple(list_chromosome)

    @staticmethod
    def reverse_sublist(chromosome):
        """
        This mutation operator swaps two chromosome.
        """
        # Ensure that the two index positions are different.
        (indx_1, indx_2) = sorted(sample(list(range(len(chromosome))), 2))
        chromosome[indx_1:indx_2] = reversed(chromosome[indx_1:indx_2])

    @staticmethod
    def rotate_by(chromosome, amt):
        return chromosome[amt:] + chromosome[:amt]


class GA_World(World):
    """
    The Population holds the collection of Individuals that will undergo evolution.
    """
    fitness_target = None
    individual_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.best_ind = None
        self.generations = None
        self.mating_op = None
        self.pop_size = None
        self.tournament_size = None

        self.BEST = 'best'
        self.WORST = 'worst'

    def generate_children(self):
        parent_1 = self.gen_parent()
        parent_2 = self.gen_parent()
        (child_1, child_2) = parent_1.mate_with(parent_2)
        child_1_mutated: Individual = child_1.mutate()
        child_2_mutated: Individual = child_2.mutate()

        child_1_mutated.compute_fitness()
        child_2_mutated.compute_fitness()

        dest_1_indx = self.select_gene_index(self.WORST, self.tournament_size)
        dest_2_indx = self.select_gene_index(self.WORST, self.tournament_size)
        self.individuals[dest_1_indx] = child_1_mutated
        self.individuals[dest_2_indx] = child_2_mutated


    def gen_individual(self):
        pass

    def gen_parent(self):
        if randint(0, 99) < SimEngine.gui_get('prob_random_parent'):
            parent = self.gen_individual()
        else:
            parent_indx = self.select_gene_index(self.BEST, self.tournament_size)
            parent = self.individuals[parent_indx]
        return parent

    def get_best_individual(self):
        best_index = self.select_gene_index(self.BEST, len(self.individuals))
        best_individual = self.individuals[best_index]
        return best_individual

    def handle_event(self, event):
        if event == 'fitness_target':
            GA_World.fitness_target = SimEngine.gui_get('fitness_target')
            return
        super().handle_event(event)

    def initial_individuals(self):
        pass

    def select_gene_index(self, best_or_worst, tournament_size) -> int:
        min_or_max = min if best_or_worst == self.BEST else max
        candidate_indices = sample(range(len(self.individuals)), tournament_size)
        selected_index = min_or_max(candidate_indices, key=lambda i: self.individuals[i].discrepancy)
        return selected_index

    def set_results(self):
        self.generations += 1
        best_ind = self.get_best_individual()
        if self.best_ind is None or best_ind.discrepancy < self.best_ind.discrepancy:
            self.best_ind = best_ind
        SimEngine.gui_set('best_fitness', value=self.best_ind.fitness)
        SimEngine.gui_set('discrepancy', value=self.best_ind.discrepancy)
        SimEngine.gui_set('generations', value=self.generations)

    # noinspection PyAttributeOutsideInit
    def setup(self):
        # Create a list of Individuals as the initial population.
        self.generations = 0
        self.pop_size = SimEngine.gui_get('pop_size')
        self.tournament_size = SimEngine.gui_get('tourn_size')
        self.individuals = self.initial_individuals()
        GA_World.fitness_target = SimEngine.gui_get('fitness_target')
        self.best_ind = None
        self.set_results()

    def step(self):
        if self.best_ind and self.best_ind.discrepancy == 0:
            return

        for _ in range(self.pop_size//2):
            self.generate_children()

        self.set_results()


# ############################################## Define GUI ############################################## #
import PySimpleGUI as sg
gui_left_upper = [

                   [sg.Text('Best:', pad=(None, (0, 0))),
                    sg.Text('     0.0', key='best_fitness', pad=(None, (0, 0))),
                    sg.Text('Discrepancy:', pad=((20, 0), (0, 0))),
                    sg.Text('     0', key='discrepancy', pad=(None, (0, 0)))],

                   [sg.Text('Generations:', pad=((0, 0), (0, 0))),
                    sg.Text('000000000', key='generations', pad=(None, (0, 0))),
                    ],

                   [sg.Text('Population size', pad=((0, 5), (20, 0))),
                    sg.Slider(key='pop_size', range=(10, 500), resolution=10, default_value=100,
                              orientation='horizontal', size=(10, 20))
                    ],

                   [sg.Text('Nbr points', pad=((0, 5), (10, 0))),
                    sg.Slider(key='nbr_points', range=(10, 200), default_value=100,
                              orientation='horizontal', size=(10, 20))
                    ],

                   [sg.Text('Tournament size', pad=((0, 5), (10, 0))),
                    sg.Slider(key='tourn_size', range=(3, 15), resolution=1, default_value=7,
                              orientation='horizontal', size=(10, 20))
                    ],

                   [sg.Text('Prob move elt', pad=((0, 5), (20, 0))),
                    sg.Slider(key='move_elt_internally', range=(0, 100), default_value=20,
                              orientation='horizontal', size=(10, 20))
                    ],

                   [sg.Text('Prob reverse sublist', pad=((0, 5), (20, 0))),
                    sg.Slider(key='reverse_sublist', range=(0, 100), default_value=20,
                              orientation='horizontal', size=(10, 20))
                    ],

                   [sg.Text('Prob random parent', pad=((0, 5), (20, 0))),
                    sg.Slider(key='prob_random_parent', range=(0, 100), default_value=5,
                              orientation='horizontal', size=(10, 20))
                    ],

                   ]