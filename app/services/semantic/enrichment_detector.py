import re
from app.core.logger import get_logger

logger = get_logger("enrichment_detector")

# Palavras-chave que indicam intenção de adicionar colunas, agregações ou enriquecimentos
_ENRICHMENT_KEYWORDS = [
    r"adicione", 
    r"inclua", 
    r"traga também", 
    r"com a coluna", 
    r"com quantidade de", 
    r"com total de", 
    r"mais a coluna", 
    r"junto com",
    r"exiba também",
    r"mostre também",
    r"calculando",
    r"somando",
    r"média de"
]

_ENRICHMENT_RE = re.compile(
    r"|".join(_ENRICHMENT_KEYWORDS),
    re.IGNORECASE | re.UNICODE
)

def detect_projection_expansion(text: str) -> bool:
    """
    Detecta se a mensagem do usuário solicita a inclusão de elementos extras
    que uma listagem (SELECT *) ou contagem simples não cobriria.
    """
    if _ENRICHMENT_RE.search(text):
        return True
    
    # Detecção heurística de nomes de colunas novas sendo pedidos após o nome da tabela
    # Ex: "liste empresas e sua qtd_projetos"
    # Se houver " e " ou " com " seguido de algo que não parece ser um filtro simples
    if re.search(r"\b(e|com|mais)\s+[a-z_]{3,}\b", text, re.IGNORECASE):
        # Evitar falsos positivos simples como "status e data" (que podem ser filtros)
        # Mas na dúvida, se houver coordenação, o semantic reuse simples deve ser cauteloso
        return True

    return False
