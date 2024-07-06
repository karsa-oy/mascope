from mascope_server.api.routes.workspace_routes import workspace_router
from mascope_server.api.routes.sample_batches_routes import sample_batches_router
from mascope_server.api.routes.samples_routes import samples_router
from mascope_server.api.routes.sample_items_routes import sample_items_router
from mascope_server.api.routes.sample_files_routes import sample_files_router
from mascope_server.api.routes.calibration_routes import calibration_router
from mascope_server.api.routes.target_collections_routes import (
    target_collections_router,
)
from mascope_server.api.routes.target_collection_in_sample_batch_routes import (
    target_collection_in_sample_batch_router,
)
from mascope_server.api.routes.target_compounds_routes import target_compounds_router
from mascope_server.api.routes.target_compound_in_target_collection_routes import (
    target_compound_in_target_collection_router,
)
from mascope_server.api.routes.target_ions_routes import target_ions_router
from mascope_server.api.routes.ionization_mechanisms_routes import (
    ionization_mechanisms_router,
)
from mascope_server.api.routes.target_isotopes_routes import target_isotopes_router
from mascope_server.api.routes.match_routes import match_router
from mascope_server.api.routes.match_aggregate_routes import match_aggreagate_router
from mascope_server.api.routes.match_samples_routes import match_samples_router
from mascope_server.api.routes.match_collections_routes import match_collections_router
from mascope_server.api.routes.match_compounds_routes import match_compounds_router
from mascope_server.api.routes.match_ions_routes import match_ions_router
from mascope_server.api.routes.match_rating_routes import match_rating_router
from mascope_server.api.routes.match_isotopes_routes import match_isotopes_router
from mascope_server.api.routes.match_interferences_routes import (
    match_interferences_router,
)
from mascope_server.api.routes.attribute_templates_routes import (
    attribute_templates_router,
)
from mascope_server.api.routes.instrument_functions_routes import (
    instrument_functions_router,
)
from mascope_server.api.routes.visualization_routes import visualization_router


routers = [
    workspace_router,
    sample_batches_router,
    samples_router,
    sample_items_router,
    sample_files_router,
    calibration_router,
    target_collections_router,
    target_collection_in_sample_batch_router,
    target_compounds_router,
    target_compound_in_target_collection_router,
    target_ions_router,
    ionization_mechanisms_router,
    target_isotopes_router,
    match_router,
    match_aggreagate_router,
    match_samples_router,
    match_collections_router,
    match_compounds_router,
    match_ions_router,
    match_rating_router,
    match_interferences_router,
    match_isotopes_router,
    attribute_templates_router,
    instrument_functions_router,
    visualization_router,
]
