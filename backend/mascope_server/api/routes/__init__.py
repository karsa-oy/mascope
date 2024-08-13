from mascope_server.api.routes.attribute_templates.attribute_templates_routes import (
    attribute_templates_router,
)
from mascope_server.api.routes.calibration.calibration_routes import calibration_router
from mascope_server.api.routes.instrument_functions.instrument_functions_routes import (
    instrument_functions_router,
)
from mascope_server.api.routes.ionization_mechanisms.ionization_mechanisms_routes import (
    ionization_mechanisms_router,
)
from mascope_server.api.routes.match.aggregate.batch.match_aggregate_batch_routes import (
    match_aggregate_batch_router,
)
from mascope_server.api.routes.match.aggregate.sample.match_aggregate_sample_routes import (
    match_aggregate_sample_router,
)
from mascope_server.api.routes.match.collections.match_collections_routes import (
    match_collections_router,
)
from mascope_server.api.routes.match.compounds.match_compounds_routes import (
    match_compounds_router,
)
from mascope_server.api.routes.match.interferences.match_interferences_routes import (
    match_interferences_router,
)
from mascope_server.api.routes.match.ions.match_ions_routes import match_ions_router
from mascope_server.api.routes.match.isotopes.match_isotopes_routes import (
    match_isotopes_router,
)
from mascope_server.api.routes.match_rating.match_rating_routes import (
    match_rating_router,
)
from mascope_server.api.routes.match.match_routes import match_router
from mascope_server.api.routes.match.samples.match_samples_routes import (
    match_samples_router,
)
from mascope_server.api.routes.match.targets.sample.match_targets_sample_routes import (
    match_targets_sample_router,
)
from mascope_server.api.routes.match.targets.batch.match_targets_batch_routes import (
    match_targets_batch_router,
)
from mascope_server.api.routes.sample.batches.sample_batches_routes import (
    sample_batches_router,
)
from mascope_server.api.routes.sample.files.sample_files_routes import (
    sample_files_router,
)
from mascope_server.api.routes.sample.items.sample_items_routes import (
    sample_items_router,
)
from mascope_server.api.routes.samples.samples_routes import samples_router
from mascope_server.api.routes.target.collections.target_collections_routes import (
    target_collections_router,
)
from mascope_server.api.routes.target.associations.target_collection_in_sample_batch_routes import (
    target_collection_in_sample_batch_router,
)
from mascope_server.api.routes.target.compounds.target_compounds_routes import (
    target_compounds_router,
)
from mascope_server.api.routes.target.associations.target_compound_in_target_collection_routes import (
    target_compound_in_target_collection_router,
)
from mascope_server.api.routes.target.ions.target_ions_routes import target_ions_router
from mascope_server.api.routes.target.isotopes.target_isotopes_routes import (
    target_isotopes_router,
)
from mascope_server.api.routes.visualization.visualization_routes import (
    visualization_router,
)
from mascope_server.api.routes.workspace.workspace_routes import workspace_router


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
    match_aggregate_batch_router,
    match_aggregate_sample_router,
    match_samples_router,
    match_collections_router,
    match_compounds_router,
    match_ions_router,
    match_rating_router,
    match_interferences_router,
    match_isotopes_router,
    match_targets_sample_router,
    match_targets_batch_router,
    attribute_templates_router,
    instrument_functions_router,
    visualization_router,
]
