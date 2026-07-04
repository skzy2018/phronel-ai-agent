import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select, col, func
from .models import ActionLog
from typing import Optional, List, Any

load_dotenv() 


# SQLite database file path
sqlite_file_name = os.getenv("PHRONEL_DB_PATH", "phronel_agent.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Engine creation
engine = create_engine(sqlite_url, echo=False)

def init_db() -> None:
    """Initializes the database by creating all tables defined in models."""
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    """Returns a new database session."""
    return Session(engine)

# --- Repository Functions for ActionLog ---

def get_actions_by_status(statuses: List[str]) -> List[ActionLog]:
    """Fetch actions filtered by a list of statuses."""
    with get_session() as session:
        statement = select(ActionLog).where(col(ActionLog.status).in_(statuses)).order_by(col(ActionLog.id).desc())
        return list(session.exec(statement).all())

def get_pending_action_count() -> int:
    """Returns the count of currently pending actions."""
    with get_session() as session:
        statement = select(func.count(col(ActionLog.id))).where(ActionLog.status == "pending")
        return session.exec(statement).one()

def update_action_status(action_id: int, new_status: str) -> Optional[ActionLog]:
    """Updates the status of a specific action."""
    with get_session() as session:
        action = session.get(ActionLog, action_id)
        if action:
            action.status = new_status
            session.add(action)
            session.commit()
            session.refresh(action)
            return action
    return None

def get_active_persona() -> Any:
    """Gets the active persona, creating a default one if none exists in the DB."""
    from .models import AgentPersona
    try:
        with get_session() as session:
            # Try to find the active persona
            persona = session.exec(
                select(AgentPersona).where(AgentPersona.is_active == True)
            ).first()
            if persona:
                return persona
            
            # If none is active, find any persona
            persona = session.exec(select(AgentPersona)).first()
            if persona:
                persona.is_active = True
                session.add(persona)
                session.commit()
                session.refresh(persona)
                return persona
                
            # Create a default one if the table is empty
            default_persona = AgentPersona()
            session.add(default_persona)
            session.commit()
            session.refresh(default_persona)
            return default_persona
    except Exception:
        # Fallback to default if DB or tables are not initialized
        return AgentPersona()

def save_active_persona(name: str, role: str, tone: str, constraints: str, sales_strategy: str) -> Any:
    """Saves or updates the active persona settings in the database."""
    from .models import AgentPersona
    with get_session() as session:
        persona = session.exec(
            select(AgentPersona).where(AgentPersona.is_active == True)
        ).first()
        
        if not persona:
            persona = session.exec(select(AgentPersona)).first()
            
        if not persona:
            persona = AgentPersona()
            
        persona.name = name
        persona.role = role
        persona.tone = tone
        persona.constraints = constraints
        persona.sales_strategy = sales_strategy
        persona.is_active = True
        
        session.add(persona)
        session.commit()
        session.refresh(persona)
        return persona

def list_personas() -> List[Any]:
    """Lists all registered personas."""
    from .models import AgentPersona
    try:
        with get_session() as session:
            personas = session.exec(select(AgentPersona)).all()
            if not personas:
                default_p = AgentPersona()
                session.add(default_p)
                session.commit()
                session.refresh(default_p)
                return [default_p]
            return list(personas)
    except Exception:
        # Fallback to default in-memory list if DB/tables are not initialized yet
        return [AgentPersona(id=1, name="Phronel (Default)", is_active=True)]

def add_persona(name: str, role: str, tone: str, constraints: str, sales_strategy: str) -> Any:
    """Adds a new persona to the database."""
    from .models import AgentPersona
    with get_session() as session:
        new_p = AgentPersona(
            name=name,
            role=role,
            tone=tone,
            constraints=constraints,
            sales_strategy=sales_strategy,
            is_active=False
        )
        session.add(new_p)
        session.commit()
        session.refresh(new_p)
        return new_p

def update_persona(persona_id: int, name: str, role: str, tone: str, constraints: str, sales_strategy: str) -> Optional[Any]:
    """Updates an existing persona's fields."""
    from .models import AgentPersona
    with get_session() as session:
        persona = session.get(AgentPersona, persona_id)
        if persona:
            persona.name = name
            persona.role = role
            persona.tone = tone
            persona.constraints = constraints
            persona.sales_strategy = sales_strategy
            session.add(persona)
            session.commit()
            session.refresh(persona)
            return persona
    return None

def delete_persona(persona_id: int) -> bool:
    """Deletes a persona. Returns False if it is active or doesn't exist."""
    from .models import AgentPersona
    with get_session() as session:
        persona = session.get(AgentPersona, persona_id)
        if not persona:
            return False
        if persona.is_active:
            # Cannot delete currently active persona
            return False
        session.delete(persona)
        session.commit()
        return True

def activate_persona(persona_id: int) -> bool:
    """Sets a persona as the active one and deactivates all others."""
    from .models import AgentPersona
    with get_session() as session:
        target = session.get(AgentPersona, persona_id)
        if not target:
            return False
            
        # Deactivate all active ones
        active_personas = session.exec(select(AgentPersona).where(AgentPersona.is_active == True)).all()
        for p in active_personas:
            p.is_active = False
            session.add(p)
            
        # Activate target
        target.is_active = True
        session.add(target)
        session.commit()
        return True
