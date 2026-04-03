"""Tests for question_loader.py — all 25 questions with 3 tests each.

Each question has:
- PASS: response agrees with ontology → score 1.0
- FAIL: response contradicts ontology → score 0.0
- NON-PARSE: response has no ontology terms → parse_success=False

Uses a small test ontology mirroring APOLLO-SV hierarchy — no download needed.
"""

import rdflib
from rdflib import Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL

import owlrl
import pytest

from apollo_eval.ontology import Ontology, ScoreResult
from apollo_eval.vocab import OntologyVocabularyBuilder
from apollo_eval.question import Question
from apollo_eval.question_loader import (
    build_question_bank,
    get_question_map,
    add_scenario_instances,
    SCENARIO,
    INFECTIOUS_DISEASE, DISEASE, EPIDEMIC, INFECTION_IN_ECOSYSTEM,
    INFECTION, INFECTION_ACQUISITION,
    INFECTIOUS_DISEASE_CONTROL_STRATEGY, INDIVIDUAL_TREATMENT_CONTROL_STRATEGY,
    VACCINATION_CONTROL_STRATEGY, QUARANTINE_CONTROL_STRATEGY,
    TREATMENT, VACCINATION, DRUG_TREATMENT,
    PATHOGEN, HOST, ORGANISM, ECOSYSTEM,
    INFECTIOUS_DISEASE_SCENARIO, CASE_DEFINITION,
    POPULATION_INFECTION_SURVEY, POPULATION_SURVEY,
    BASIC_REPRODUCTION_NUMBER, VACCINATION_EFFICACY, EPIDEMIC_MODEL,
    PATHOGENIC_DISPOSITION, IMMUNOCOMPETENCE,
    MATERIAL_ENTITY, DISORDER, PROCESS, PLAN_SPECIFICATION,
    IS_ABOUT, CAUSALLY_UPSTREAM_OF, IMMEDIATELY_PRECEDED_BY,
    BEARER_OF, HAS_PARTICIPANT, OCCURS_IN,
)

OBO = Namespace("http://purl.obolibrary.org/obo/")
IMMATERIAL_ENTITY = OBO["BFO_0000141"]


def _build_test_ontology():
    """Build a minimal ontology mirroring the APOLLO-SV hierarchy for testing."""
    g = rdflib.Graph()

    # --- Class hierarchy ---
    g.add((DISEASE, RDF.type, OWL.Class))
    g.add((DISEASE, RDFS.label, Literal("disease")))
    g.add((INFECTIOUS_DISEASE, RDF.type, OWL.Class))
    g.add((INFECTIOUS_DISEASE, RDFS.subClassOf, DISEASE))
    g.add((INFECTIOUS_DISEASE, RDFS.label, Literal("infectious disease")))

    g.add((PROCESS, RDF.type, OWL.Class))
    g.add((PROCESS, RDFS.label, Literal("process")))
    g.add((INFECTION_IN_ECOSYSTEM, RDF.type, OWL.Class))
    g.add((INFECTION_IN_ECOSYSTEM, RDFS.subClassOf, PROCESS))
    g.add((INFECTION_IN_ECOSYSTEM, RDFS.label, Literal("infection in ecosystem")))
    g.add((EPIDEMIC, RDF.type, OWL.Class))
    g.add((EPIDEMIC, RDFS.subClassOf, INFECTION_IN_ECOSYSTEM))
    g.add((EPIDEMIC, RDFS.label, Literal("epidemic")))

    g.add((INFECTION, RDF.type, OWL.Class))
    g.add((INFECTION, RDFS.label, Literal("infection")))
    g.add((INFECTION_ACQUISITION, RDF.type, OWL.Class))
    g.add((INFECTION_ACQUISITION, RDFS.label, Literal("infection acquisition")))

    g.add((PLAN_SPECIFICATION, RDF.type, OWL.Class))
    g.add((PLAN_SPECIFICATION, RDFS.label, Literal("plan specification")))
    g.add((INFECTIOUS_DISEASE_CONTROL_STRATEGY, RDF.type, OWL.Class))
    g.add((INFECTIOUS_DISEASE_CONTROL_STRATEGY, RDFS.subClassOf, PLAN_SPECIFICATION))
    g.add((INFECTIOUS_DISEASE_CONTROL_STRATEGY, RDFS.label, Literal("infectious disease control strategy")))
    g.add((INDIVIDUAL_TREATMENT_CONTROL_STRATEGY, RDF.type, OWL.Class))
    g.add((INDIVIDUAL_TREATMENT_CONTROL_STRATEGY, RDFS.subClassOf, INFECTIOUS_DISEASE_CONTROL_STRATEGY))
    g.add((INDIVIDUAL_TREATMENT_CONTROL_STRATEGY, RDFS.label, Literal("individual treatment control strategy")))
    g.add((VACCINATION_CONTROL_STRATEGY, RDF.type, OWL.Class))
    g.add((VACCINATION_CONTROL_STRATEGY, RDFS.subClassOf, INDIVIDUAL_TREATMENT_CONTROL_STRATEGY))
    g.add((VACCINATION_CONTROL_STRATEGY, RDFS.label, Literal("vaccination control strategy")))
    g.add((QUARANTINE_CONTROL_STRATEGY, RDF.type, OWL.Class))
    g.add((QUARANTINE_CONTROL_STRATEGY, RDFS.subClassOf, INFECTIOUS_DISEASE_CONTROL_STRATEGY))
    g.add((QUARANTINE_CONTROL_STRATEGY, RDFS.label, Literal("quarantine control strategy")))

    g.add((TREATMENT, RDF.type, OWL.Class))
    g.add((TREATMENT, RDFS.label, Literal("treatment")))
    g.add((VACCINATION, RDF.type, OWL.Class))
    g.add((VACCINATION, RDFS.subClassOf, TREATMENT))
    g.add((VACCINATION, RDFS.label, Literal("vaccination")))
    g.add((DRUG_TREATMENT, RDF.type, OWL.Class))
    g.add((DRUG_TREATMENT, RDFS.subClassOf, TREATMENT))
    g.add((DRUG_TREATMENT, RDFS.label, Literal("drug treatment")))

    g.add((MATERIAL_ENTITY, RDF.type, OWL.Class))
    g.add((MATERIAL_ENTITY, RDFS.label, Literal("material entity")))
    g.add((ORGANISM, RDF.type, OWL.Class))
    g.add((ORGANISM, RDFS.subClassOf, MATERIAL_ENTITY))
    g.add((ORGANISM, RDFS.label, Literal("organism")))
    g.add((PATHOGEN, RDF.type, OWL.Class))
    g.add((PATHOGEN, RDFS.subClassOf, ORGANISM))
    g.add((PATHOGEN, RDFS.label, Literal("pathogen")))
    g.add((HOST, RDF.type, OWL.Class))
    g.add((HOST, RDFS.subClassOf, ORGANISM))
    g.add((HOST, RDFS.label, Literal("host")))

    g.add((ECOSYSTEM, RDF.type, OWL.Class))
    g.add((ECOSYSTEM, RDFS.label, Literal("ecosystem")))
    g.add((INFECTIOUS_DISEASE_SCENARIO, RDF.type, OWL.Class))
    g.add((INFECTIOUS_DISEASE_SCENARIO, RDFS.label, Literal("infectious disease scenario")))
    g.add((CASE_DEFINITION, RDF.type, OWL.Class))
    g.add((CASE_DEFINITION, RDFS.label, Literal("case definition")))
    g.add((POPULATION_SURVEY, RDF.type, OWL.Class))
    g.add((POPULATION_SURVEY, RDFS.label, Literal("population survey")))
    g.add((POPULATION_INFECTION_SURVEY, RDF.type, OWL.Class))
    g.add((POPULATION_INFECTION_SURVEY, RDFS.subClassOf, POPULATION_SURVEY))
    g.add((POPULATION_INFECTION_SURVEY, RDFS.label, Literal("population infection survey")))
    g.add((BASIC_REPRODUCTION_NUMBER, RDF.type, OWL.Class))
    g.add((BASIC_REPRODUCTION_NUMBER, RDFS.label, Literal("basic reproduction number")))
    g.add((VACCINATION_EFFICACY, RDF.type, OWL.Class))
    g.add((VACCINATION_EFFICACY, RDFS.label, Literal("vaccination efficacy")))
    g.add((EPIDEMIC_MODEL, RDF.type, OWL.Class))
    g.add((EPIDEMIC_MODEL, RDFS.label, Literal("epidemic model")))

    g.add((PATHOGENIC_DISPOSITION, RDF.type, OWL.Class))
    g.add((PATHOGENIC_DISPOSITION, RDFS.label, Literal("pathogenic disposition")))
    g.add((IMMUNOCOMPETENCE, RDF.type, OWL.Class))
    g.add((IMMUNOCOMPETENCE, RDFS.label, Literal("immunocompetence")))
    g.add((DISORDER, RDF.type, OWL.Class))
    g.add((DISORDER, RDFS.label, Literal("disorder")))
    g.add((IMMATERIAL_ENTITY, RDF.type, OWL.Class))
    g.add((IMMATERIAL_ENTITY, RDFS.label, Literal("immaterial entity")))

    # --- Disjointness ---
    g.add((ORGANISM, OWL.disjointWith, DISORDER))
    g.add((PATHOGENIC_DISPOSITION, OWL.disjointWith, DISEASE))
    g.add((PATHOGENIC_DISPOSITION, OWL.disjointWith, IMMUNOCOMPETENCE))
    g.add((IMMUNOCOMPETENCE, OWL.disjointWith, DISEASE))
    g.add((MATERIAL_ENTITY, OWL.disjointWith, IMMATERIAL_ENTITY))

    # --- Object properties ---
    for prop, label in [
        (IS_ABOUT, "is about"), (CAUSALLY_UPSTREAM_OF, "causally upstream of"),
        (IMMEDIATELY_PRECEDED_BY, "immediately preceded by"),
        (BEARER_OF, "bearer of"), (HAS_PARTICIPANT, "has participant"),
        (OCCURS_IN, "occurs in"),
    ]:
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.label, Literal(label)))

    # Apply reasoning before vocabulary building
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return OntologyVocabularyBuilder(g).build()


@pytest.fixture
def question_bank():
    """Build the full question bank against the test ontology."""
    ontology = _build_test_ontology()
    Question.ontology = ontology
    questions = build_question_bank(ontology)
    yield questions
    Question.ontology = None


@pytest.fixture
def qmap(question_bank):
    return get_question_map(question_bank)


# =========================================================================
# Structural tests
# =========================================================================

class TestQuestionBankStructure:
    def test_bank_has_25_questions(self, question_bank):
        assert len(question_bank) == 25

    def test_unique_question_ids(self, question_bank):
        ids = [q.question_id for q in question_bank]
        assert len(ids) == len(set(ids))

    def test_all_have_prompts(self, question_bank):
        for q in question_bank:
            assert q.prompt, f"Question {q.question_id} has empty prompt"

    def test_question_map(self, question_bank):
        qmap = get_question_map(question_bank)
        assert len(qmap) == 25

    def test_scenario_instances_in_graph(self, question_bank):
        graph = Question.ontology.graph
        assert (SCENARIO.measles_epidemic, RDF.type, EPIDEMIC) in graph
        assert (SCENARIO.vaccination_strategy, RDF.type, VACCINATION_CONTROL_STRATEGY) in graph
        assert (SCENARIO.measles_pathogen, RDF.type, PATHOGEN) in graph


# =========================================================================
# Q1–Q12: Class Membership — pass / fail / non-parse per question
# =========================================================================

class TestQ01:
    """epidemic instance is an epidemic (direct type)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000001"].score("A measles epidemic is an epidemic event.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000001"].score("A measles epidemic is not an epidemic.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000001"].score("It is a sudden outbreak of illness.")
        assert r.parse_success is False


class TestQ02:
    """epidemic is an infection in ecosystem (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000002"].score("Yes, an epidemic is a type of infection in ecosystem.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000002"].score("No, an epidemic is not an infection in ecosystem.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000002"].score("It spreads through communities.")
        assert r.parse_success is False


class TestQ03:
    """vaccination strategy is a vaccination control strategy (direct)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000003"].score("It is a vaccination control strategy.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000003"].score("It is not a vaccination control strategy.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000003"].score("It is a plan for prevention.")
        assert r.parse_success is False


class TestQ04:
    """vaccination control strategy is individual treatment control strategy (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000004"].score("Yes, a vaccination control strategy is an individual treatment control strategy.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000004"].score("No, a vaccination control strategy is not an individual treatment control strategy.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000004"].score("It targets specific patients.")
        assert r.parse_success is False


class TestQ05:
    """vaccination control strategy is infectious disease control strategy (entailed chain)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000005"].score("A vaccination control strategy is an infectious disease control strategy.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000005"].score("A vaccination control strategy is not an infectious disease control strategy.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000005"].score("It helps prevent spread.")
        assert r.parse_success is False


class TestQ06:
    """quarantine control strategy is infectious disease control strategy (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000006"].score("Yes, a quarantine control strategy is an infectious disease control strategy.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000006"].score("No, a quarantine control strategy is not an infectious disease control strategy.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000006"].score("It involves isolating people.")
        assert r.parse_success is False


class TestQ07:
    """vaccination treatment is a vaccination (direct)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000007"].score("Vaccination is classified as a vaccination procedure.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000007"].score("Vaccination is not actually a vaccination in the formal sense.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000007"].score("It is an injection given to patients.")
        assert r.parse_success is False


class TestQ08:
    """vaccination is a treatment (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000008"].score("Yes, vaccination is a type of treatment.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000008"].score("Vaccination is not a treatment.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000008"].score("It is a preventive measure.")
        assert r.parse_success is False


class TestQ09:
    """drug treatment is a treatment (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000009"].score("Drug treatment is a type of treatment.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000009"].score("Drug treatment is not a treatment.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000009"].score("Patients take medication.")
        assert r.parse_success is False


class TestQ10:
    """pathogen is a pathogen (direct)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000010"].score("The causative agent is classified as a pathogen.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000010"].score("The agent is not a pathogen.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000010"].score("It causes illness in people.")
        assert r.parse_success is False


class TestQ11:
    """pathogen is an organism (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000011"].score("Yes, a pathogen is a type of organism.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000011"].score("A pathogen is not an organism.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000011"].score("It is a living thing.")
        assert r.parse_success is False


class TestQ12:
    """population infection survey is a population survey (entailed)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000012"].score("A population infection survey is a type of population survey.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000012"].score("A population infection survey is not a population survey.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0001-4000-8000-000000000012"].score("It collects data on illness rates.")
        assert r.parse_success is False


# =========================================================================
# Q13–Q20: Property Restriction — pass / fail / non-parse per question
# =========================================================================

class TestQ13:
    """scenario is about ecosystem (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000013"].score("An infectious disease scenario is about an ecosystem.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000013"].score("An infectious disease scenario is not about an ecosystem.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000013"].score("It models environmental conditions.")
        assert r.parse_success is False


class TestQ14:
    """infection acquisition causally upstream of infection (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000014"].score("Infection acquisition leads to infection.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000014"].score("Infection acquisition does not lead to infection.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000014"].score("Exposure causes illness.")
        assert r.parse_success is False


class TestQ15:
    """infection immediately preceded by infection acquisition (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000015"].score("Infection is preceded by infection acquisition.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000015"].score("Infection is not preceded by infection acquisition.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000015"].score("One stage follows another in sequence.")
        assert r.parse_success is False


class TestQ16:
    """pathogen bearer of pathogenic disposition (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000016"].score("A pathogen bears a pathogenic disposition.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000016"].score("A pathogen does not bear a pathogenic disposition.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000016"].score("It has the ability to cause harm.")
        assert r.parse_success is False


class TestQ17:
    """vaccination has participant host (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000017"].score("Vaccination has a host as participant.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000017"].score("Vaccination does not have a host as participant.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000017"].score("A patient receives the injection.")
        assert r.parse_success is False


class TestQ18:
    """epidemic occurs in ecosystem (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000018"].score("An epidemic occurs in an ecosystem.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000018"].score("An epidemic does not occur in an ecosystem.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000018"].score("It happens in a community.")
        assert r.parse_success is False


class TestQ19:
    """infection acquisition has participant pathogen (pyshacl)"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000019"].score("Infection acquisition involves a pathogen.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000019"].score("Infection acquisition does not involve a pathogen.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000019"].score("The microbe enters the body.")
        assert r.parse_success is False


class TestQ20:
    """vaccination does NOT have pathogen as participant — absence in graph"""
    def test_pass(self, qmap):
        # Correctly negating: graph lacks this triple, negation = consistent
        r = qmap["c3a1e8f0-0002-4000-8000-000000000020"].score("Vaccination does not involve a pathogen as participant.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        # Incorrectly affirming: graph lacks this triple, affirmation = inconsistent
        r = qmap["c3a1e8f0-0002-4000-8000-000000000020"].score("Vaccination involves a pathogen as participant.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0002-4000-8000-000000000020"].score("The procedure targets the immune system.")
        assert r.parse_success is False


# =========================================================================
# Q21–Q25: Disjointness — pass / fail / non-parse per question
# =========================================================================

class TestQ21:
    """organism disjointWith disorder — pathogen is NOT a disorder"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000021"].score("No, a pathogen cannot be a disorder.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000021"].score("A pathogen is a disorder.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000021"].score("They are fundamentally different categories.")
        assert r.parse_success is False


class TestQ22:
    """pathogenic disposition disjointWith disease"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000022"].score("No, a pathogenic disposition is not a disease.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000022"].score("A pathogenic disposition is a disease.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000022"].score("They refer to different concepts.")
        assert r.parse_success is False


class TestQ23:
    """pathogenic disposition disjointWith immunocompetence"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000023"].score("No, pathogenic disposition and immunocompetence are not the same.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000023"].score("Pathogenic disposition is immunocompetence.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000023"].score("These are separate biological attributes.")
        assert r.parse_success is False


class TestQ24:
    """host is NOT a disease"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000024"].score("No, a host is not a disease.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000024"].score("A host is a disease.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000024"].score("The individual harbors the condition.")
        assert r.parse_success is False


class TestQ25:
    """material entity disjointWith immaterial entity — pathogen is material"""
    def test_pass(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000025"].score("No, a pathogen cannot be an immaterial entity.")
        assert r.parse_success and r.score == 1.0

    def test_fail(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000025"].score("A pathogen is an immaterial entity.")
        assert r.parse_success and r.score == 0.0

    def test_nonparse(self, qmap):
        r = qmap["c3a1e8f0-0003-4000-8000-000000000025"].score("It has physical substance.")
        assert r.parse_success is False


# =========================================================================
# Cross-cutting tests
# =========================================================================

class TestAllQuestionsParsing:
    def test_all_handle_empty_response(self, question_bank):
        for q in question_bank:
            r = q.score("")
            assert isinstance(r, ScoreResult)
            assert r.parse_success is False

    def test_all_handle_gibberish(self, question_bank):
        for q in question_bank:
            r = q.score("asdfghjkl zxcvbnm qwertyuiop 12345")
            assert isinstance(r, ScoreResult)
            assert r.parse_success is False

    def test_no_exceptions(self, question_bank):
        for q in question_bank:
            for resp in ["", "I don't know.", "Yes.", "No."]:
                r = q.score(resp)
                assert isinstance(r, ScoreResult)
