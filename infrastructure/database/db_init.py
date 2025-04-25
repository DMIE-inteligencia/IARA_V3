import os
import logging
import argparse
import hashlib
from infrastructure.database.connection import init_db, engine, Base, SessionLocal
from infrastructure.database.models import User
from infrastructure.database.repository import UserRepository

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db_init")

def _hash_password(password: str) -> str:
    """Cria um hash seguro da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user(username, password):
    """Cria um usuário administrador no sistema"""
    # Gerar o hash da senha
    password_hash = _hash_password(password)
    
    # Criar usuário no banco de dados
    with SessionLocal() as db:
        user_repo = UserRepository(db)
        
        # Verificar se já existe um usuário com este nome
        existing_user = user_repo.get_user_by_username(username)
        if existing_user:
            logger.info(f"Usuário {username} já existe, pulando criação")
            return
        
        try:
            user = user_repo.create_user(
                username=username,
                password_hash=password_hash,
                email=f"{username}@iara.com.br"
            )
            logger.info(f"Usuário administrador {username} criado com sucesso (ID: {user.id})")
        except Exception as e:
            logger.error(f"Erro ao criar usuário administrador: {str(e)}")
            raise

def main():
    """Função principal para inicializar o banco de dados"""
    parser = argparse.ArgumentParser(description="Inicialização do banco de dados do IARA")
    parser.add_argument("--create-admin", action="store_true", help="Criar usuário administrador")
    parser.add_argument("--admin-username", default="admin", help="Nome do usuário administrador")
    parser.add_argument("--admin-password", default="password", help="Senha do usuário administrador")
    args = parser.parse_args()
    
    # Inicializar o banco de dados
    logger.info("Inicializando o banco de dados...")
    try:
        init_db()
        logger.info("Banco de dados inicializado com sucesso")
        
        # Criar usuário administrador, se solicitado
        if args.create_admin:
            logger.info(f"Criando usuário administrador: {args.admin_username}")
            create_admin_user(args.admin_username, args.admin_password)
            
    except Exception as e:
        logger.error(f"Erro durante a inicialização do banco de dados: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())