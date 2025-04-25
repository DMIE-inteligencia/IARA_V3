import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.pool import QueuePool

# Configuração do logger
logger = logging.getLogger("database")

# Obter a URL do banco de dados a partir das variáveis de ambiente
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("A variável de ambiente DATABASE_URL não está definida")

# Criar engine de conexão
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
    connect_args={
        "sslmode": "prefer",  # Preferir SSL, mas não exigir
        "connect_timeout": 10  # Timeout de conexão em segundos
    }
)

# Criar Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Classe base para todos os modelos
class ModelBase:
    """Classe base para todos os modelos do IARA"""
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

# Função para obter uma sessão do banco de dados
def get_db():
    """Obtém uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função para inicializar o banco de dados
def init_db():
    """Inicializa o banco de dados criando todas as tabelas"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar o banco de dados: {str(e)}")
        raise