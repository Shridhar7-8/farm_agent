from typing import Dict, Any, Optional
import logging
from config import config
from utils import VertexAIFactory, JsonUtils, logger

# ============================================================================
# SYSTEM INSTRUCTION CONSTANTS
# ============================================================================

PLANNING_SYSTEM_INSTRUCTION = """You are an Expert Agricultural Planning Agent specializing in decomposing complex farming problems into actionable steps.

**Your Core Function:**
Break down complex agricultural challenges into clear, sequential, actionable plans that farmers can implement.

**Planning Framework:**
1. **Problem Analysis**: Understand the farming challenge, constraints, and goals
2. **Task Decomposition**: Break into logical, sequential steps
3. **Resource Planning**: Identify required materials, tools, timing
4. **Risk Assessment**: Consider weather, market, and operational risks
5. **Success Metrics**: Define measurable outcomes for each step

**Output Structure:**
```json
{
    "problem_analysis": "Clear analysis of the farming challenge",
    "goal": "Primary objective to achieve",
    "steps": [
        {
            "step_number": 1,
            "action": "Specific action to take",
            "description": "Detailed explanation of what to do",
            "timeline": "When to execute (days/weeks/months)",
            "resources_needed": ["List of materials/tools/inputs needed"],
            "dependencies": ["Previous steps that must be completed"],
            "success_criteria": "How to measure success of this step",
            "potential_risks": ["Risks to consider"],
            "alternatives": ["Backup options if this approach fails"]
        }
    ],
    "critical_path": ["Most important steps that cannot be delayed"],
    "total_timeline": "Overall time to complete the plan",
    "budget_considerations": "Cost factors to consider",
    "success_indicators": "Overall measures of plan success"
}
```

**Guidelines:**
- Be specific with quantities, timing, and methods
- Consider Indian farming conditions and practices
- Include both traditional and modern approaches when relevant
- Consider seasonal factors, weather patterns, and market timing
- Provide practical alternatives for resource constraints
- Focus on implementable, step-by-step actions"""

REFLECTION_SYSTEM_INSTRUCTION = """You are an Expert Agricultural Quality Assurance Agent implementing the Producer-Critic reflection pattern.

**Your Role:** Critically evaluate agricultural advice for accuracy, safety, practicality, and completeness.

**Evaluation Criteria:**

1. **Technical Accuracy (25%)**
   - Are the agricultural facts and methods correct?
   - Are dosages, quantities, and measurements accurate?
   - Is the timing advice appropriate for crops/seasons?

2. **Safety Assessment (25%)**  
   - Are pesticide/fertilizer recommendations safe and legal?
   - Could the advice harm crops, soil, or farmer health?
   - Are safety precautions mentioned where needed?

3. **Practicality (25%)**
   - Can an average farmer realistically implement this advice?
   - Are resource requirements reasonable and accessible?
   - Is the advice suitable for Indian farming conditions?

4. **Completeness (25%)**
   - Does the advice address the farmer's actual question?
   - Are important details or steps missing?
   - Are potential risks or alternatives mentioned?

**Scoring System:** 0.0 to 1.0 (0.75+ is acceptable for production)

**Output Format:**
```json
{
    "overall_quality_score": 0.85,
    "evaluation_summary": "Brief assessment of advice quality",
    "dimension_scores": {
        "technical_accuracy": 0.9,
        "safety_assessment": 0.8, 
        "practicality": 0.85,
        "completeness": 0.8
    },
    "strengths": ["What the advice does well"],
    "concerns": ["Issues or gaps identified"],
    "improvement_suggestions": ["Specific recommendations to enhance the advice"],
    "risk_flags": ["Any safety or critical issues"],
    "approval_status": "approved|needs_revision|rejected",
    "revision_priority": "low|medium|high",
    "farmer_readiness": "Can farmers implement this safely and effectively?"
}
```

**Guidelines:**
- Be thorough but fair in evaluation
- Focus on farmer safety and practical implementation
- Consider Indian agricultural context and conditions  
- Flag any dangerous or misleading advice immediately
- Provide constructive suggestions for improvement"""

REFINEMENT_SYSTEM_INSTRUCTION = """You are an Agricultural Plan Refinement Specialist focused on improving farming plans based on quality feedback.

**Your Role:** Take an existing agricultural plan and quality evaluation, then create an improved version that addresses identified concerns and gaps.

**Refinement Process:**
1. Analyze the quality evaluation feedback
2. Identify specific areas for improvement
3. Address safety concerns and technical inaccuracies
4. Enhance practicality and completeness
5. Maintain the original plan structure while improving quality

**Guidelines:**
- Address all concerns mentioned in the evaluation
- Improve technical accuracy and safety measures
- Enhance practical implementation details
- Add missing steps or information
- Maintain clear structure and farmer-friendly language
- Focus on implementable solutions for Indian farming conditions

**Output:** Return the refined plan in the same JSON structure as the original plan."""


# ============================================================================
# FARMING PLANNING AGENT
# ============================================================================

class FarmingPlanningAgent:
    """
    Decomposes complex farming problems into actionable steps.
    Implements the Planning Design Pattern for agricultural decision-making.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('farm_agent.planning')
        self.logger.info("FarmingPlanningAgent initialized")
        
    async def create_farming_plan(self, problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Decomposes a complex farming problem into actionable steps.
        
        Args:
            problem_description: The farming challenge or goal
            context: Additional context (weather, location, crops, etc.)
            
        Returns:
            Detailed plan with steps, priorities, and timeline
        """
        try:
            VertexAIFactory.init_vertexai(config)
            
            planning_model = VertexAIFactory.create_model(
                model_name=config.vertexai.model_name,
                system_instruction=PLANNING_SYSTEM_INSTRUCTION
            )

            context_info = ""
            if context:
                context_info = f"""

**Available Context:**
- Location: {context.get('location', 'Not specified')}
- Current Season: {context.get('season', 'Not specified')}
- Crop Type: {context.get('crop_type', 'Not specified')}
- Farm Size: {context.get('farm_size', 'Not specified')}
- Budget Range: {context.get('budget', 'Not specified')}
- Experience Level: {context.get('experience', 'Not specified')}
- Available Resources: {context.get('resources', 'Not specified')}
"""

            planning_prompt = f"""

**FARMING CHALLENGE TO PLAN:**
{problem_description}

{context_info}

**TASK:** Create a comprehensive, step-by-step farming plan for this challenge. 
Focus on practical, implementable actions with clear timelines and resource requirements.
Consider Indian farming conditions, seasonal factors, and provide alternatives for different resource levels.

Respond with a detailed JSON plan following the exact structure specified in your instructions."""

            self.logger.debug("-----------------------------------------------------------")
            self.logger.debug("LLM Request to Planning model:")
            self.logger.debug(f"Problem Description: {problem_description}")
            self.logger.debug("-----------------------------------------------------------")
            
            response = planning_model.generate_content(planning_prompt)
            
            self.logger.debug("-----------------------------------------------------------")
            self.logger.debug("LLM Response from Planning model:")
            if response and response.text:
                self.logger.debug(f"Response length: {len(response.text)} characters")
                
                plan_data = JsonUtils.extract_and_parse_json(response.text)
                
                if plan_data:
                    self.logger.info(f"Planning agent generated farming plan successfully")
                    return {
                        "status": "success",
                        "plan": plan_data,
                        "message": "Comprehensive farming plan generated successfully"
                    }
                else:
                    return {
                        "status": "success",
                        "plan": {"detailed_plan": response.text},
                        "message": "Comprehensive farming plan generated successfully"
                    }
            else:
                self.logger.error("LLM Response failed: No text received from planning model")
                return {
                    "status": "error",
                    "message": "Failed to generate farming plan"
                }
                
        except Exception as e:
            self.logger.error(f"Error in farming planning agent: {e}")
            return {
                "status": "error",
                "message": f"Planning agent error: {str(e)}"
            }


# ============================================================================
# REFLECTION AGENT
# ============================================================================

class ReflectionAgent:
    """
    Implements Producer-Critic model for quality assurance and self-correction.
    Evaluates agricultural advice for accuracy, safety, and practicality.
    """
    
    def __init__(self):
        self.quality_threshold = config.quality_threshold
        self.logger = logging.getLogger('farm_agent.planning')
        self.logger.info("ReflectionAgent initialized")
        
    async def evaluate_agricultural_advice(self, advice: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Evaluates agricultural advice using producer-critic methodology.
        
        Args:
            advice: The agricultural advice to evaluate
            context: Context including query, farmer info, etc.
            
        Returns:
            Quality evaluation with score, feedback, and improvement suggestions
        """
        try:
            VertexAIFactory.init_vertexai(config)
                
            reflection_model = VertexAIFactory.create_model(
                model_name=config.vertexai.model_name,
                system_instruction=REFLECTION_SYSTEM_INSTRUCTION
            )

            context_info = ""
            if context:
                context_info = f"""

**Evaluation Context:**
- Original Query: {context.get('query', 'Not provided')}
- Farmer Location: {context.get('location', 'Not specified')}
- Crop/Topic: {context.get('crop_type', 'Not specified')}
- Farmer Experience: {context.get('experience', 'Not specified')}
- Season/Timing: {context.get('season', 'Not specified')}
"""

            evaluation_prompt = f"""

**AGRICULTURAL ADVICE TO EVALUATE:**
{advice}

{context_info}

**TASK:** Conduct a comprehensive quality evaluation of this agricultural advice.
Rate it across all four dimensions, identify strengths and concerns, and provide improvement suggestions.
Focus on accuracy, safety, practicality for Indian farmers, and completeness.

Respond with a detailed JSON evaluation following the exact structure specified."""

            response = reflection_model.generate_content(evaluation_prompt)
            
            if response and response.text:
                evaluation_data = JsonUtils.extract_and_parse_json(response.text)
                
                if evaluation_data:
                    self.logger.info(f"Reflection agent completed quality evaluation")
                    return {
                        "status": "success",
                        "evaluation": evaluation_data,
                        "meets_threshold": evaluation_data.get('overall_quality_score', 0.0) >= self.quality_threshold,
                        "message": "Quality evaluation completed successfully"
                    }
                else:
                    return {
                        "status": "success",
                        "evaluation": {"quality_assessment": response.text},
                        "meets_threshold": True,
                        "message": "Quality evaluation completed successfully"
                    }
            else:
                return {
                    "status": "error",
                    "message": "Failed to generate evaluation"
                }
                
        except Exception as e:
            self.logger.error(f"Error in reflection agent: {e}")
            return {
                "status": "error",
                "message": f"Reflection agent error: {str(e)}"
            }


# ============================================================================
# SEQUENTIAL PLANNING AGENT
# ============================================================================

class SequentialPlanningAgent:
    """
    Production-Grade Sequential Planning Agent that combines Planning + Reflection.
    Implements Producer-Critic pattern with real-time progress visibility.
    
    **Workflow:**
    1. Planning Phase: Generate comprehensive agricultural plan
    2. Reflection Phase: Evaluate plan quality and safety
    3. Refinement Phase: Improve plan if needed (iterative)
    4. Delivery Phase: Present final validated plan
    """

    def __init__(self):
        self.logger = logging.getLogger('farm_agent.planning')
        self.logger.info("Initializing SequentialPlanningAgent with Producer-Critic pattern")
        
        self.quality_threshold = config.quality_threshold
        self.max_refinement_iterations = config.max_refinement_iterations
        
    def _print_progress(self, phase: str, message: str, status: str = ""):
        """Display real-time progress to user."""
        print(f"\n{status} **{phase}:** {message}")
        
    async def create_validated_agricultural_plan(self, problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Creates a comprehensive, quality-validated agricultural plan with real-time progress.
        
        Args:
            problem_description: The farming challenge or goal
            context: Additional context (location, crops, resources, etc.)
            
        Returns:
            Final validated plan with quality metrics and process details
        """
        try:
            self.logger.info(f"Starting sequential planning for: {problem_description[:100]}...")
            self.logger.debug(f"Planning context: {context}")
            self._print_progress("SEQUENTIAL PLANNING SYSTEM", "Initializing production-grade planning workflow...")
            
            VertexAIFactory.init_vertexai(config)
            
            # ========================================================================
            # PHASE 1: PLANNING GENERATION
            # ========================================================================
            self.logger.info("PHASE 1: Starting agricultural plan generation")
            self._print_progress("PHASE 1 - PLANNING", "Analyzing problem and generating comprehensive plan...", "🌱")
            
            plan_result = await self._generate_agricultural_plan(problem_description, context)
            
            if plan_result["status"] != "success":
                self.logger.error(f"PHASE 1 FAILED: Planning generation error - {plan_result.get('message', 'Unknown error')}")
                return {
                    "status": "error",
                    "message": f"Planning failed: {plan_result.get('message', 'Unknown error')}",
                    "phase": "planning"
                }
            
            self._print_progress("PHASE 1 - PLANNING", "✅ Plan generated successfully! Moving to quality assessment...", "")
            
            # ========================================================================
            # PHASE 2: REFLECTION & QUALITY ASSESSMENT
            # ========================================================================
            self.logger.info("PHASE 2: Starting plan reflection and quality assessment")
            self._print_progress("PHASE 2 - REFLECTION", "Evaluating plan quality, safety, and practicality...", "🔍")
            
            plan_text = self._extract_plan_text(plan_result["plan"])
            self.logger.debug(f"Extracted plan text for evaluation: {len(plan_text)} characters")
            evaluation_result = await self._evaluate_plan_quality(plan_text, context, problem_description)
            
            if evaluation_result["status"] != "success":
                self._print_progress("PHASE 2 - REFLECTION", "⚠️ Quality check failed, proceeding with original plan", "")
                return {
                    "status": "partial_success",
                    "final_plan": plan_result["plan"],
                    "message": "Plan created but quality validation failed",
                    "quality_check": "failed"
                }
            
            quality_score = evaluation_result["evaluation"].get("overall_quality_score", 0.0)
            self._print_progress("PHASE 2 - REFLECTION", f"Quality Score: {quality_score:.2f} (Threshold: {self.quality_threshold})", "📊")
            
            # ========================================================================
            # PHASE 3: REFINEMENT (IF NEEDED)
            # ========================================================================
            refinement_count = 0
            current_plan = plan_result["plan"]
            current_evaluation = evaluation_result["evaluation"]
            
            while (quality_score < self.quality_threshold and 
                   refinement_count < self.max_refinement_iterations):
                
                refinement_count += 1
                self._print_progress("PHASE 3 - REFINEMENT", f"Quality below threshold. Refining plan (Attempt {refinement_count}/{self.max_refinement_iterations})...", "🔧")
                
                refinement_result = await self._refine_plan(
                    current_plan, 
                    current_evaluation, 
                    problem_description, 
                    context
                )
                
                if refinement_result["status"] == "success":
                    current_plan = refinement_result["refined_plan"]
                    
                    refined_plan_text = self._extract_plan_text(current_plan)
                    new_evaluation_result = await self._evaluate_plan_quality(refined_plan_text, context, problem_description)
                    
                    if new_evaluation_result["status"] == "success":
                        quality_score = new_evaluation_result["evaluation"].get("overall_quality_score", 0.0)
                        current_evaluation = new_evaluation_result["evaluation"]
                        self._print_progress("PHASE 3 - REFINEMENT", f"Refined Quality Score: {quality_score:.2f}", "✨")
                    else:
                        break
                else:
                    self._print_progress("PHASE 3 - REFINEMENT", "Refinement failed, using previous version", "⚠️")
                    break
            
            # ========================================================================
            # PHASE 4: FINAL DELIVERY
            # ========================================================================
            final_status = "approved" if quality_score >= self.quality_threshold else "conditionally_approved"
            
            if final_status == "approved":
                self._print_progress("PHASE 4 - DELIVERY", "✅ Plan approved! High-quality agricultural guidance ready.", "")
            else:
                self._print_progress("PHASE 4 - DELIVERY", f"⚠️ Plan conditionally approved (Score: {quality_score:.2f})", "")
            
            return {
                "status": "success",
                "final_plan": current_plan,
                "quality_evaluation": current_evaluation,
                "quality_score": quality_score,
                "approval_status": final_status,
                "refinement_iterations": refinement_count,
                "process_summary": {
                    "planning_phase": "completed",
                    "reflection_phase": "completed", 
                    "refinement_phase": f"{refinement_count} iterations",
                    "final_approval": final_status
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in sequential planning agent: {e}")
            self._print_progress("ERROR", f"Sequential planning failed: {str(e)}", "❌")
            return {
                "status": "error",
                "message": f"Sequential planning error: {str(e)}"
            }

    async def _generate_agricultural_plan(self, problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate initial agricultural plan (Phase 1)."""
        planning_model = VertexAIFactory.create_model(
            model_name=config.vertexai.model_name,
            system_instruction=PLANNING_SYSTEM_INSTRUCTION
        )

        context_info = ""
        if context:
            context_info = f"""

**Available Context:**
- Location: {context.get('location', 'Not specified')}
- Current Season: {context.get('season', 'Not specified')}
- Crop Type: {context.get('crop_type', 'Not specified')}
- Farm Size: {context.get('farm_size', 'Not specified')}
- Budget Range: {context.get('budget', 'Not specified')}
- Experience Level: {context.get('experience', 'Not specified')}
- Available Resources: {context.get('resources', 'Not specified')}
"""
        
        planning_prompt = f"""

**FARMING CHALLENGE TO PLAN:**
{problem_description}

{context_info}

**TASK:** Create a comprehensive, step-by-step farming plan for this challenge. 
Focus on practical, implementable actions with clear timelines and resource requirements.
Consider Indian farming conditions, seasonal factors, and provide alternatives for different resource levels.

Respond with a detailed JSON plan following the exact structure specified in your instructions."""

        response = planning_model.generate_content(planning_prompt)
        
        if response and response.text:
            plan_data = JsonUtils.extract_and_parse_json(response.text)
            
            if plan_data:
                self.logger.info(f"Sequential planning agent created plan with {len(plan_data.get('steps', []))} steps")
                return {
                    "status": "success",
                    "plan": plan_data,
                    "raw_response": response.text
                }
            else:
                self.logger.warning("Failed to parse JSON plan")
                return {
                    "status": "partial_success",
                    "plan": {"raw_plan": response.text},
                    "message": "Plan generated but not in structured format"
                }
        else:
            return {
                "status": "error",
                "message": "Failed to generate farming plan"
            }

    async def _evaluate_plan_quality(self, plan_text: str, context: Optional[Dict] = None, original_query: str = "") -> Dict[str, Any]:
        """Evaluate plan quality and safety (Phase 2)."""
        reflection_model = VertexAIFactory.create_model(
            model_name=config.vertexai.model_name,
            system_instruction=REFLECTION_SYSTEM_INSTRUCTION
        )

        context_info = ""
        if context:
            context_info = f"""

**Evaluation Context:**
- Original Query: {original_query}
- Farmer Location: {context.get('location', 'Not specified')}
- Crop/Topic: {context.get('crop_type', 'Not specified')}
- Farmer Experience: {context.get('experience', 'Not specified')}
- Season/Timing: {context.get('season', 'Not specified')}
"""
        
        evaluation_prompt = f"""

**AGRICULTURAL PLAN TO EVALUATE:**
{plan_text}

{context_info}

**TASK:** Conduct a comprehensive quality evaluation of this agricultural plan.
Rate it across all four dimensions, identify strengths and concerns, and provide improvement suggestions.
Focus on accuracy, safety, practicality for Indian farmers, and completeness.

Respond with a detailed JSON evaluation following the exact structure specified."""

        response = reflection_model.generate_content(evaluation_prompt)
        
        if response and response.text:
            evaluation_data = JsonUtils.extract_and_parse_json(response.text)
            
            if evaluation_data:
                quality_score = evaluation_data.get('overall_quality_score', 0.0)
                self.logger.info(f"Sequential reflection evaluated plan with quality score: {quality_score}")
                return {
                    "status": "success",
                    "evaluation": evaluation_data,
                    "meets_threshold": quality_score >= self.quality_threshold,
                    "raw_response": response.text
                }
            else:
                self.logger.warning("Failed to parse JSON evaluation")
                return {
                    "status": "partial_success",
                    "evaluation": {"raw_evaluation": response.text},
                    "meets_threshold": False,
                    "message": "Evaluation generated but not in structured format"
                }
        else:
            return {
                "status": "error",
                "message": "Failed to generate evaluation"
            }

    async def _refine_plan(self, current_plan: Dict[str, Any], evaluation: Dict[str, Any], problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Refine plan based on evaluation feedback (Phase 3)."""
        refinement_model = VertexAIFactory.create_model(
            model_name=config.vertexai.model_name,
            system_instruction=REFINEMENT_SYSTEM_INSTRUCTION
        )

        improvement_suggestions = evaluation.get("improvement_suggestions", [])
        concerns = evaluation.get("concerns", [])
        risk_flags = evaluation.get("risk_flags", [])
        
        refinement_prompt = f"""**ORIGINAL PROBLEM:**
{problem_description}

**CURRENT PLAN TO REFINE:**
{JsonUtils.safe_dumps(current_plan)}

**QUALITY EVALUATION FEEDBACK:**
- Overall Score: {evaluation.get('overall_quality_score', 0.0)}
- Concerns: {concerns}
- Improvement Suggestions: {improvement_suggestions}  
- Risk Flags: {risk_flags}
- Approval Status: {evaluation.get('approval_status', 'unknown')}

**TASK:** Create an improved version of this agricultural plan that addresses all the identified concerns and implements the improvement suggestions. Maintain the same JSON structure but enhance the content quality, safety, and practicality.

Focus on:
1. Addressing safety concerns and risk flags
2. Improving technical accuracy  
3. Enhancing practical implementation details
4. Adding missing information or steps
5. Making it more suitable for Indian farming conditions

Respond with the refined plan in the same JSON format."""

        response = refinement_model.generate_content(refinement_prompt)
        
        if response and response.text:
            refined_plan = JsonUtils.extract_and_parse_json(response.text)
            
            if refined_plan:
                self.logger.info("Successfully refined agricultural plan")
                return {
                    "status": "success",
                    "refined_plan": refined_plan,
                    "raw_response": response.text
                }
            else:
                return {
                    "status": "error",
                    "message": "Refined plan not in expected JSON format"
                }
        else:
            return {
                "status": "error",
                "message": "Failed to generate refined plan"
            }

    def _extract_plan_text(self, plan_data: Dict[str, Any]) -> str:
        """Extract text from plan data for evaluation."""
        if isinstance(plan_data, dict):
            if "raw_plan" in plan_data:
                return plan_data["raw_plan"]
            else:
                return JsonUtils.safe_dumps(plan_data)
        else:
            return str(plan_data)


# ============================================================================
# INITIALIZE AGENTS
# ============================================================================

farming_planner = FarmingPlanningAgent()
reflection_agent = ReflectionAgent()
sequential_planner = SequentialPlanningAgent()

logger.info("Planning agents initialized successfully")