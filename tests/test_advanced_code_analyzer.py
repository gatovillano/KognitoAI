import pytest
from utils.advanced_code_analyzer import (
    CodeAnalysisResult,
    CodeStructureItem,
    DesignPatternItem,
    DependencyItem,
    SecurityAnalysisItem,
    PerformanceAnalysisItem,
    RefactoringOpportunityItem,
    DocumentationHealthItem,
    PotentialIssueItem,
    RecommendationItem,
)
from skills.analysis_and_insights_skill.scripts.analyze_code_for_insights_tool import AnalyzeCodeForInsightsTool

def test_code_analysis_result_instantiation():
    # Verify we can instantiate CodeAnalysisResult with objects or dictionaries
    result = CodeAnalysisResult(
        executive_summary="Hello world",
        code_structure=[
            CodeStructureItem(component="MyComp", description="Desc"),
            {"component": "DictComp", "description": "DictDesc"} # Pydantic should auto-coerce or allow
        ],
        design_patterns=[
            DesignPatternItem(pattern="Singleton", description="Single desc")
        ],
        dependencies=[
            DependencyItem(library="numpy", description="math")
        ],
        security_analysis=[
            SecurityAnalysisItem(vulnerability="XSS", description="danger", severity="High")
        ],
        performance_analysis=[
            PerformanceAnalysisItem(area="DB", issue="slow queries", suggestion="index")
        ],
        refactoring_opportunities=[
            RefactoringOpportunityItem(concept="clean", description="cleanup", benefit="maintainability")
        ],
        documentation_health=[
            DocumentationHealthItem(item="docstring", status="Good", recommendation="keep up")
        ],
        potential_issues=[
            PotentialIssueItem(issue="bug", description="buggy")
        ],
        recommendations=[
            RecommendationItem(recommendation="rec", rationale="rat", application="app", implementation="impl")
        ]
    )
    
    assert result.executive_summary == "Hello world"
    assert len(result.code_structure) == 2
    assert result.code_structure[0].component == "MyComp"
    assert result.code_structure[1].component == "DictComp"

def test_format_result():
    tool = AnalyzeCodeForInsightsTool()
    
    result = CodeAnalysisResult(
        executive_summary="Sample summary",
        code_structure=[
            CodeStructureItem(component="MyComp", description="My description")
        ],
        design_patterns=[
            DesignPatternItem(pattern="Singleton", description="Patterns desc")
        ]
    )
    
    formatted = tool._format_result(result, "all")
    assert "Sample summary" in formatted
    assert "MyComp" in formatted
    assert "My description" in formatted
    assert "Singleton" in formatted
    assert "Patterns desc" in formatted
    assert "{" not in formatted  # should not be formatted as raw dictionary string
