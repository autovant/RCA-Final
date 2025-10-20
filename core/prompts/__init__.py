"""
Prompt template management for RCA analysis.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import json
from pathlib import Path

from core.config import settings

# Default prompt templates
DEFAULT_PROMPTS = {
    "rca_analysis": {
        "name": "Root Cause Analysis",
        "description": "Standard RCA prompt for analyzing log files and identifying root causes",
        "system_prompt": """You are an expert Site Reliability Engineer and DevOps specialist. 
Your role is to analyze log files, identify root causes of issues, and provide actionable remediation steps.
Focus on precision, clarity, and practical solutions.""",
        "user_prompt_template": """Job ID: {job_id}
Scenario: {mode}

Provide a concise root cause assessment and remediation plan based on the following file summaries:

All file content has been sanitized to remove personal or secret information before this request.

{file_summaries}

Focus on likely causes, impacted areas, and actionable remediation steps.

Please structure your response with:
1. **Executive Summary**: A one-line assessment of the primary issue
2. **Root Cause Analysis**: Detailed analysis of what went wrong and why
3. **Impact Assessment**: What systems/users were affected
4. **Recommended Actions**: Prioritized list of remediation steps
5. **Prevention**: Long-term measures to prevent recurrence""",
        "variables": ["job_id", "mode", "file_summaries"],
        "editable": True
    },
    "quick_analysis": {
        "name": "Quick Analysis",
        "description": "Fast analysis for simple issues",
        "system_prompt": """You are a technical analyst providing quick insights.""",
        "user_prompt_template": """Analyze the following logs and provide a brief summary:

{file_summaries}

Keep your response concise and actionable.""",
        "variables": ["file_summaries"],
        "editable": True
    },
    "detailed_forensics": {
        "name": "Detailed Forensics",
        "description": "Deep dive forensic analysis for complex incidents",
        "system_prompt": """You are a senior security and systems forensics expert.
Provide comprehensive analysis with attention to security implications, performance issues, and system architecture.""",
        "user_prompt_template": """Job ID: {job_id}
Analysis Type: Detailed Forensic Investigation

Conduct a thorough forensic analysis of the following system logs:

{file_summaries}

Provide:
1. **Timeline Reconstruction**: Chronological sequence of events
2. **Root Cause Deep Dive**: Technical analysis with evidence
3. **Security Assessment**: Any security implications
4. **Performance Analysis**: System performance issues identified
5. **Architectural Review**: Design/configuration issues
6. **Detailed Remediation Plan**: Step-by-step recovery and prevention""",
        "variables": ["job_id", "file_summaries"],
        "editable": True
    }
}


class PromptTemplateManager:
    """Manages prompt templates for LLM analysis."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/prompts.json")
        self._templates: Dict[str, Any] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load templates from config file or use defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._templates = json.load(f)
            except Exception:
                # Fall back to defaults on error
                self._templates = DEFAULT_PROMPTS.copy()
        else:
            self._templates = DEFAULT_PROMPTS.copy()
    
    def _save_templates(self) -> None:
        """Save templates to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._templates, f, indent=2)
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific prompt template."""
        return self._templates.get(template_name)
    
    def list_templates(self) -> Dict[str, Any]:
        """List all available templates."""
        return {
            name: {
                "name": tpl.get("name", name),
                "description": tpl.get("description", ""),
                "editable": tpl.get("editable", True),
                "variables": tpl.get("variables", [])
            }
            for name, tpl in self._templates.items()
        }
    
    def update_template(
        self, 
        template_name: str, 
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Update an existing template."""
        if template_name not in self._templates:
            return False
        
        template = self._templates[template_name]
        if not template.get("editable", True):
            return False
        
        if system_prompt is not None:
            template["system_prompt"] = system_prompt
        if user_prompt_template is not None:
            template["user_prompt_template"] = user_prompt_template
        if description is not None:
            template["description"] = description
        
        self._save_templates()
        return True
    
    def create_template(
        self,
        template_name: str,
        name: str,
        description: str,
        system_prompt: str,
        user_prompt_template: str,
        variables: list[str]
    ) -> bool:
        """Create a new custom template."""
        if template_name in self._templates:
            return False
        
        self._templates[template_name] = {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template,
            "variables": variables,
            "editable": True,
            "custom": True
        }
        
        self._save_templates()
        return True
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a custom template."""
        if template_name not in self._templates:
            return False
        
        template = self._templates[template_name]
        if not template.get("custom", False):
            return False  # Can't delete built-in templates
        
        del self._templates[template_name]
        self._save_templates()
        return True
    
    def reset_to_defaults(self) -> None:
        """Reset all templates to defaults."""
        self._templates = DEFAULT_PROMPTS.copy()
        self._save_templates()
    
    def format_prompt(
        self, 
        template_name: str, 
        **kwargs: Any
    ) -> tuple[Optional[str], Optional[str]]:
        """Format a prompt template with variables."""
        template = self.get_template(template_name)
        if not template:
            return None, None
        
        try:
            system_prompt = template["system_prompt"]
            user_prompt = template["user_prompt_template"].format(**kwargs)
            return system_prompt, user_prompt
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")


# Global instance
_prompt_manager: Optional[PromptTemplateManager] = None


def get_prompt_manager() -> PromptTemplateManager:
    """Get the global prompt template manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptTemplateManager()
    return _prompt_manager


__all__ = [
    "PromptTemplateManager",
    "get_prompt_manager",
    "DEFAULT_PROMPTS",
]
