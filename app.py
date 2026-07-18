import os

from flask import Flask

from config import Config


# ==========================================================
# Authentication
# ==========================================================

from routes.auth_routes import auth_bp


# ==========================================================
# Core Dashboard
# ==========================================================

from routes.dashboard_routes import dashboard_bp
from routes.data_routes import data_bp
from routes.analytics_routes import analytics_bp
from routes.executive_routes import executive_bp
from routes.forecast_routes import forecast_bp
from routes.export_routes import export_bp


# ==========================================================
# AI Dataset Assistant
# ==========================================================

from routes.ai_assistant_routes import ai_bp


# ==========================================================
# Workspace
# ==========================================================

from routes.workspace_routes import workspace_bp
from routes.workspace_page_routes import workspace_page_bp
from routes.workspace_detail_routes import workspace_detail_bp
from routes.workspace_version_routes import workspace_version_bp


# ==========================================================
# Collaboration
# ==========================================================

from routes.collaboration_routes import collaboration_bp
from routes.collaboration_page_routes import collaboration_page_bp


# ==========================================================
# Enterprise AI
# ==========================================================

from routes.enterprise_ai_routes import enterprise_ai_bp

from routes.enterprise_ai_page_routes import (
    enterprise_ai_page_bp
)


# ==========================================================
# R2.5 Advanced Intelligence
# ==========================================================

from routes.advanced_analytics_routes import (
    advanced_analytics_bp
)

from routes.advanced_analytics_page_routes import (
    advanced_analytics_page_bp
)

from routes.copilot_history_routes import (
    copilot_history_bp
)

from routes.reporting_center_routes import (
    reporting_center_bp
)
from routes.ai_sql_assistant_routes import ai_sql_bp
from routes.ml_studio_routes import ml_studio_bp
from routes.automl_routes import automl_bp
from routes.phase4_routes import phase4_bp


# ==========================================================
# Database and Service Initializers
# ==========================================================

from services.workspace_service import (
    init_workspace_database
)

from services.collaboration_service import (
    init_collaboration_database
)

from services.enterprise_ai_database import (
    init_enterprise_ai_database
)

from services.copilot_history_service import (
    init_copilot_history_database
)

from services.workspace_version_service import (
    init_workspace_version_database
)

from services.performance_cache_service import (
    init_cache_directory
)


# ==========================================================
# Application Factory
# ==========================================================

def create_app():
    """
    Create and configure the Flask application.
    """

    app = Flask(
        __name__
    )

    # ------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------

    app.config.from_object(
        Config
    )

    # ------------------------------------------------------
    # Create required directories
    # ------------------------------------------------------

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True
    )

    os.makedirs(
        os.path.join(
            app.root_path,
            "exports"
        ),
        exist_ok=True
    )

    # ------------------------------------------------------
    # Initialize databases and services
    # ------------------------------------------------------

    with app.app_context():
        init_workspace_database()
        init_collaboration_database()
        init_enterprise_ai_database()
        init_copilot_history_database()
        init_workspace_version_database()
        init_cache_directory()

    # ------------------------------------------------------
    # Register authentication
    # ------------------------------------------------------

    app.register_blueprint(
        auth_bp
    )

    # ------------------------------------------------------
    # Register core dashboard blueprints
    # ------------------------------------------------------

    app.register_blueprint(
        dashboard_bp
    )

    app.register_blueprint(
        data_bp
    )

    app.register_blueprint(
        analytics_bp
    )

    app.register_blueprint(
        forecast_bp
    )

    app.register_blueprint(
        executive_bp
    )

    app.register_blueprint(
        export_bp
    )

    # ------------------------------------------------------
    # Register AI Dataset Assistant
    # ------------------------------------------------------

    app.register_blueprint(
        ai_bp
    )

    # ------------------------------------------------------
    # Register workspace blueprints
    # ------------------------------------------------------

    app.register_blueprint(
        workspace_bp
    )

    app.register_blueprint(
        workspace_page_bp
    )

    app.register_blueprint(
        workspace_detail_bp
    )

    app.register_blueprint(
        workspace_version_bp
    )

    # ------------------------------------------------------
    # Register collaboration blueprints
    # ------------------------------------------------------

    app.register_blueprint(
        collaboration_bp
    )

    app.register_blueprint(
        collaboration_page_bp
    )

    # ------------------------------------------------------
    # Register Enterprise AI blueprints
    # ------------------------------------------------------

    app.register_blueprint(
        enterprise_ai_bp
    )

    app.register_blueprint(
        enterprise_ai_page_bp
    )

    # ------------------------------------------------------
    # Register advanced intelligence blueprints
    # ------------------------------------------------------

    app.register_blueprint(
        advanced_analytics_bp
    )

    app.register_blueprint(
        advanced_analytics_page_bp
    )

    app.register_blueprint(
        copilot_history_bp
    )

    app.register_blueprint(
        reporting_center_bp
    )
    
    app.register_blueprint(ai_sql_bp)
    app.register_blueprint(ml_studio_bp)
    app.register_blueprint(automl_bp)
    app.register_blueprint(phase4_bp)
    return app


# ==========================================================
# Create Application
# ==========================================================

app = create_app()


# ==========================================================
# Development Server
# ==========================================================

if __name__ == "__main__":
    app.run(
        debug=True
    )