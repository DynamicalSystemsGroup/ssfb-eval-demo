"""Tests for question_loader.py — all 25 questions with mocked responses.

Each test verifies:
- parse_success=True when response contains ontology terms
- score=1.0 when the graph supports the claim (consistent)
- score=0.0 when the graph does not support the claim (inconsistent)
- parse_success=False when response contains no ontology terms

Uses a small test ontology that mirrors the relevant APOLLO-SV class hierarchy,
property assertions, and disjointness axioms — avoids downloading the full OWL file.
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
    # Class IRIs
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
    # Property IRIs
    IS_ABOUT, CAUSALLY_UPSTREAM_OF, IMMEDIATELY_PRECEDED_BY,
    BEARER_OF, HAS_PARTICIPANT, OCCURS_IN,
)

OBO = Namespace("http://purl.obolibrary.org/obo/")
IMMATERIAL_ENTITY = OBO["BFO_0000141"]


def _build_test_ontology():
    """Build a minimal ontology mirroring the APOLLO-SV hierarchy for testing.

    Includes class hierarchy, disjointness axioms, and labels needed by
    the PhraseMatcher for extraction. Does NOT require downloading APOLLO-SV.
    """
    g = rdflib.Graph()

    # --- Class hierarchy ---
    # Disease hierarchy
    g.add((DISEASE, RDF.type, OWL.Class))
    g.add((DISEASE, RDFS.label, Literal("disease")))
    g.add((INFECTIOUS_DISEASE, RDF.type, OWL.Class))
    g.add((INFECTIOUS_DISEASE, RDFS.subClassOf, DISEASE))
    g.add((INFECTIOUS_DISEASE, RDFS.label, Literal("infectious disease")))

    # Epidemic hierarchy
    g.add((PROCESS, RDF.type, OWL.Class))
    g.add((PROCESS, RDFS.label, Literal("process")))
    g.add((INFECTION_IN_ECOSYSTEM, RDF.type, OWL.Class))
    g.add((INFECTION_IN_ECOSYSTEM, RDFS.subClassOf, PROCESS))
    g.add((INFECTION_IN_ECOSYSTEM, RDFS.label, Literal("infection in ecosystem")))
    g.add((EPIDEMIC, RDF.type, OWL.Class))
    g.add((EPIDEMIC, RDFS.subClassOf, INFECTION_IN_ECOSYSTEM))
    g.add((EPIDEMIC, RDFS.label, Literal("epidemic")))

    # Infection processes
    g.add((INFECTION, RDF.type, OWL.Class))
    g.add((INFECTION, RDFS.label, Literal("infection")))
    g.add((INFECTION_ACQUISITION, RDF.type, OWL.Class))
    g.add((INFECTION_ACQUISITION, RDFS.label, Literal("infection acquisition")))

    # Control strategy hierarchy
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

    # Treatment hierarchy
    g.add((TREATMENT, RDF.type, OWL.Class))
    g.add((TREATMENT, RDFS.label, Literal("treatment")))
    g.add((VACCINATION, RDF.type, OWL.Class))
    g.add((VACCINATION, RDFS.subClassOf, TREATMENT))
    g.add((VACCINATION, RDFS.label, Literal("vaccination")))
    g.add((DRUG_TREATMENT, RDF.type, OWL.Class))
    g.add((DRUG_TREATMENT, RDFS.subClassOf, TREATMENT))
    g.add((DRUG_TREATMENT, RDFS.label, Literal("drug treatment")))

    # Organism hierarchy
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

    # Ecosystem
    g.add((ECOSYSTEM, RDF.type, OWL.Class))
    g.add((ECOSYSTEM, RDFS.label, Literal("ecosystem")))

    # Data classes
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

    # Dispositions
    g.add((PATHOGENIC_DISPOSITION, RDF.type, OWL.Class))
    g.add((PATHOGENIC_DISPOSITION, RDFS.label, Literal("pathogenic disposition")))
    g.add((IMMUNOCOMPETENCE, RDF.type, OWL.Class))
    g.add((IMMUNOCOMPETENCE, RDFS.label, Literal("immunocompetence")))

    # Disorder
    g.add((DISORDER, RDF.type, OWL.Class))
    g.add((DISORDER, RDFS.label, Literal("disorder")))
    g.add((IMMATERIAL_ENTITY, RDF.type, OWL.Class))
    g.add((IMMATERIAL_ENTITY, RDFS.label, Literal("immaterial entity")))

    # --- Disjointness axioms ---
    g.add((ORGANISM, OWL.disjointWith, DISORDER))
    g.add((PATHOGENIC_DISPOSITION, OWL.disjointWith, DISEASE))
    g.add((PATHOGENIC_DISPOSITION, OWL.disjointWith, IMMUNOCOMPETENCE))
    g.add((IMMUNOCOMPETENCE, OWL.disjointWith, DISEASE))
    g.add((MATERIAL_ENTITY, OWL.disjointWith, IMMATERIAL_ENTITY))

    # --- Object properties ---
    g.add((IS_ABOUT, RDF.type, OWL.ObjectProperty))
    g.add((IS_ABOUT, RDFS.label, Literal("is about")))
    g.add((CAUSALLY_UPSTREAM_OF, RDF.type, OWL.ObjectProperty))
    g.add((CAUSALLY_UPSTREAM_OF, RDFS.label, Literal("causally upstream of")))
    g.add((IMMEDIATELY_PRECEDED_BY, RDF.type, OWL.ObjectProperty))
    g.add((IMMEDIATELY_PRECEDED_BY, RDFS.label, Literal("immediately preceded by")))
    g.add((BEARER_OF, RDF.type, OWL.ObjectProperty))
    g.add((BEARER_OF, RDFS.label, Literal("bearer of")))
    g.add((HAS_PARTICIPANT, RDF.type, OWL.ObjectProperty))
    g.add((HAS_PARTICIPANT, RDFS.label, Literal("has participant")))
    g.add((OCCURS_IN, RDF.type, OWL.ObjectProperty))
    g.add((OCCURS_IN, RDFS.label, Literal("occurs in")))

    # Apply OWL RL reasoning
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
    """Question map for easy lookup by ID."""
    return get_question_map(question_bank)


# =========================================================================
# Structural tests
# =========================================================================

class TestQuestionBankStructure:
    # Req: question bank has exactly 25 questions
    def test_bank_has_25_questions(self, question_bank):
        assert len(question_bank) == 25

    # Req: all question_ids are unique
    def test_unique_question_ids(self, question_bank):
        ids = [q.question_id for q in question_bank]
        assert len(ids) == len(set(ids))

    # Req: all questions have non-empty prompts
    def test_all_have_prompts(self, question_bank):
        for q in question_bank:
            assert q.prompt, f"Question {q.question_id} has empty prompt"

    # Req: get_question_map returns correct mapping
    def test_question_map(self, question_bank):
        qmap = get_question_map(question_bank)
        assert len(qmap) == 25
        for q in question_bank:
            assert qmap[q.question_id] is q

    # Req: scenario instances are added to the graph
    def test_scenario_instances_in_graph(self, question_bank):
        graph = Question.ontology.graph
        assert (SCENARIO.measles_epidemic, RDF.type, EPIDEMIC) in graph
        assert (SCENARIO.vaccination_strategy, RDF.type, VACCINATION_CONTROL_STRATEGY) in graph
        assert (SCENARIO.measles_pathogen, RDF.type, PATHOGEN) in graph


# =========================================================================
# Class Membership Questions (Q1–Q12) — mocked response scoring
# =========================================================================

class TestClassMembershipScoring:
    # Q1: epidemic is an epidemic (direct type)
    def test_q1_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000001"].score(
            "A measles epidemic is classified as an epidemic event."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q2: epidemic is an infection in ecosystem (entailed)
    def test_q2_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000002"].score(
            "Yes, an epidemic is a type of infection in ecosystem."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q3: vaccination strategy is a vaccination control strategy (direct)
    def test_q3_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000003"].score(
            "It is a vaccination control strategy."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q4: vaccination control strategy is individual treatment control strategy (entailed)
    def test_q4_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000004"].score(
            "Yes, a vaccination control strategy is an individual treatment control strategy."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q5: vaccination control strategy is infectious disease control strategy (entailed via chain)
    def test_q5_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000005"].score(
            "A vaccination control strategy is an infectious disease control strategy."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q6: quarantine control strategy is infectious disease control strategy (entailed)
    def test_q6_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000006"].score(
            "Yes, a quarantine control strategy is an infectious disease control strategy."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q7: vaccination treatment is a vaccination (direct)
    def test_q7_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000007"].score(
            "Vaccination is classified as a vaccination procedure."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q8: vaccination is a treatment (entailed)
    def test_q8_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000008"].score(
            "Yes, vaccination is a type of treatment used to prevent disease."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q9: drug treatment is a treatment (entailed)
    def test_q9_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000009"].score(
            "Drug treatment is a type of treatment."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q10: pathogen is a pathogen (direct)
    def test_q10_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000010"].score(
            "The causative agent is classified as a pathogen."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q11: pathogen is an organism (entailed)
    def test_q11_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000011"].score(
            "Yes, a pathogen is a type of organism."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q12: population infection survey is a population survey (entailed)
    def test_q12_consistent(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000012"].score(
            "A population infection survey is a type of population survey."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: parse failure when response has no ontology terms
    def test_class_membership_parse_failure(self, qmap):
        result = qmap["c3a1e8f0-0001-4000-8000-000000000001"].score(
            "It is a sudden outbreak of illness affecting many people."
        )
        assert result.parse_success is False


# =========================================================================
# Property Restriction Questions (Q13–Q20) — mocked response scoring
# =========================================================================

class TestPropertyRestrictionScoring:
    # Q13: scenario is about ecosystem (pyshacl)
    def test_q13_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000013"].score(
            "An infectious disease scenario is about an ecosystem."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q14: infection acquisition causally upstream of infection (pyshacl)
    def test_q14_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000014"].score(
            "Infection acquisition is causally upstream of infection."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q15: infection immediately preceded by infection acquisition (pyshacl)
    def test_q15_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000015"].score(
            "Infection is immediately preceded by infection acquisition."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q16: pathogen bearer of pathogenic disposition (pyshacl)
    def test_q16_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000016"].score(
            "A pathogen bears a pathogenic disposition."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q17: vaccination has participant host (pyshacl)
    def test_q17_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000017"].score(
            "Vaccination has a host as a participant."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q18: epidemic occurs in ecosystem (pyshacl)
    def test_q18_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000018"].score(
            "An epidemic occurs in an ecosystem."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q19: infection acquisition has participant pathogen (pyshacl)
    def test_q19_consistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000019"].score(
            "Infection acquisition involves a pathogen as a participant."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q20: vaccination does NOT have pathogen as participant — score should be 0.0
    # Req: score 0.0 when property-value not in graph
    def test_q20_inconsistent(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000020"].score(
            "Vaccination involves a pathogen as a participant."
        )
        assert result.parse_success is True
        assert result.score == 0.0

    # Req: parse failure when response has no ontology terms
    def test_property_restriction_parse_failure(self, qmap):
        result = qmap["c3a1e8f0-0002-4000-8000-000000000013"].score(
            "It concerns the natural world and living systems."
        )
        assert result.parse_success is False


# =========================================================================
# Disjointness Questions (Q21–Q25) — mocked response scoring
# =========================================================================

class TestDisjointnessScoring:
    # Q21: pathogen (organism) is NOT a disorder — consistent with disjointness
    def test_q21_consistent(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000021"].score(
            "No, a pathogen is an organism and cannot be a disorder."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q22: pathogenic disposition is NOT a disease — consistent with disjointness
    def test_q22_consistent(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000022"].score(
            "A pathogenic disposition is not a disease — they are distinct."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q23: pathogenic disposition is NOT immunocompetence — consistent with disjointness
    def test_q23_consistent(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000023"].score(
            "No, pathogenic disposition and immunocompetence are disjoint."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q24: host is NOT a disease — consistent
    def test_q24_consistent(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000024"].score(
            "A host is not a disease."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Q25: pathogen (material entity) is NOT an immaterial entity — consistent
    def test_q25_consistent(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000025"].score(
            "A pathogen is a material entity and cannot be an immaterial entity."
        )
        assert result.parse_success is True
        assert result.score == 1.0

    # Req: parse failure when response has no ontology terms
    def test_disjointness_parse_failure(self, qmap):
        result = qmap["c3a1e8f0-0003-4000-8000-000000000021"].score(
            "These two categories are fundamentally different."
        )
        assert result.parse_success is False


# =========================================================================
# Cross-cutting tests
# =========================================================================

class TestAllQuestionsParsing:
    # Req: every question handles empty response gracefully
    def test_all_handle_empty_response(self, question_bank):
        for q in question_bank:
            result = q.score("")
            assert isinstance(result, ScoreResult), f"Question {q.question_id} failed on empty response"
            assert result.parse_success is False

    # Req: every question handles gibberish gracefully
    def test_all_handle_gibberish(self, question_bank):
        for q in question_bank:
            result = q.score("asdfghjkl zxcvbnm qwertyuiop 12345")
            assert isinstance(result, ScoreResult), f"Question {q.question_id} failed on gibberish"
            assert result.parse_success is False

    # Req: no exceptions escape score() for any question
    def test_no_exceptions(self, question_bank):
        responses = [
            "",
            "I don't know.",
            "Yes.",
            "No.",
            "The answer involves vaccination and treatment of infectious disease.",
        ]
        for q in question_bank:
            for resp in responses:
                result = q.score(resp)
                assert isinstance(result, ScoreResult)
