"""
Skill Loader: carrega arquivos .md de skills e os concatena ao prompt do agente.
"""
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.skill import SkillInfo

logger = get_logger("skill_loader")


def load_skill(skill_id: str, skills_dir: Optional[Path] = None) -> Optional[str]:
    """
    Carrega o conteúdo de uma skill.
    
    Args:
        skill_id: Nome da skill (sem .md).
        skills_dir: Diretório de skills (usa settings.skills_path se None).
        
    Returns:
        Conteúdo da skill ou None se não encontrada.
    """
    dir_path = skills_dir or settings.skills_path
    skill_file = dir_path / f"{skill_id}.md"

    if not skill_file.exists():
        logger.warning(f"Skill não encontrada: {skill_file}")
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")
        if not content.strip():
            logger.warning(f"Skill vazia: {skill_id}")
            return None
        return content
    except Exception as e:
        logger.error(f"Erro ao ler skill '{skill_id}': {e}")
        return None


def load_skills_for_agent(skill_ids: list[str], skills_dir: Optional[Path] = None) -> str:
    """
    Carrega múltiplas skills e as concatena em um bloco.
    
    Returns:
        Texto concatenado de todas as skills válidas.
    """
    if not skill_ids:
        return ""

    blocks = []
    for skill_id in skill_ids:
        content = load_skill(skill_id, skills_dir)
        if content:
            blocks.append(f"## SKILL: {skill_id}\n\n{content}")
            logger.debug(f"Skill carregada: {skill_id}")
        else:
            logger.warning(f"Skill não carregada: {skill_id}")

    if not blocks:
        return ""

    return "\n\n---\n\n".join(blocks)


def list_available_skills(skills_dir: Optional[Path] = None) -> list[SkillInfo]:
    """
    Lista todas as skills disponíveis no diretório de skills.
    
    Returns:
        Lista de SkillInfo com metadados das skills.
    """
    dir_path = skills_dir or settings.skills_path
    if not dir_path.exists():
        return []

    skills = []
    for skill_file in sorted(dir_path.glob("*.md")):
        try:
            content = skill_file.read_text(encoding="utf-8")
            stat = skill_file.stat()
            
            # Extrair título da primeira linha (# Título)
            title = skill_file.stem
            lines = content.split("\n")
            if lines and lines[0].startswith("#"):
                title = lines[0].lstrip("#").strip()
            
            # Extrair descrição (segunda linha não vazia)
            description = None
            for line in lines[1:5]:
                line = line.strip()
                if line and not line.startswith("#"):
                    description = line
                    break

            skill = SkillInfo(
                id=skill_file.stem,
                filename=skill_file.name,
                title=title,
                description=description,
                size_bytes=stat.st_size,
            )
            skills.append(skill)
        except Exception as e:
            logger.error(f"Erro ao listar skill {skill_file}: {e}")

    return skills


def get_skill_content(skill_id: str, skills_dir: Optional[Path] = None) -> Optional[SkillInfo]:
    """Retorna a skill com conteúdo completo."""
    dir_path = skills_dir or settings.skills_path
    skill_file = dir_path / f"{skill_id}.md"

    if not skill_file.exists():
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")
        stat = skill_file.stat()

        title = skill_file.stem
        lines = content.split("\n")
        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("#").strip()

        return SkillInfo(
            id=skill_file.stem,
            filename=skill_file.name,
            title=title,
            content=content,
            size_bytes=stat.st_size,
        )
    except Exception as e:
        logger.error(f"Erro ao carregar skill {skill_id}: {e}")
        return None
