import type {
  OpenAPIClient,
  Parameters,
  UnknownParamsObject,
  OperationResponse,
  AxiosRequestConfig,
} from 'openapi-client-axios';

declare namespace Components {
    namespace Schemas {
        /**
         * AggregateAndCreateMatchesBody
         */
        export interface AggregateAndCreateMatchesBody {
            /**
             * Target Ion Id
             * Filter targets by ID of the target ion
             */
            target_ion_id?: string;
            /**
             * Ion-specific filter parameters, used for match_score and sample_peak_area filtering, setting match_category
             */
            filter_params?: /* FilterParams */ FilterParams;
            /**
             * Include Match Interference
             * Include match interference data in the response
             */
            include_match_interference?: boolean;
            /**
             * Match Ions
             * Flag to determine if ion matches should be processed
             */
            match_ions?: /**
             * Match Ions
             * Flag to determine if ion matches should be processed
             */
            boolean | null;
            /**
             * Match Compounds
             * Flag to determine if compound matches should be processed
             */
            match_compounds?: /**
             * Match Compounds
             * Flag to determine if compound matches should be processed
             */
            boolean | null;
            /**
             * Match Collections
             * Flag to determine if collection matches should be processed
             */
            match_collections?: /**
             * Match Collections
             * Flag to determine if collection matches should be processed
             */
            boolean | null;
            /**
             * Match Samples
             * Flag to determine if sample matches should be processed
             */
            match_samples?: /**
             * Match Samples
             * Flag to determine if sample matches should be processed
             */
            boolean | null;
        }
        /**
         * AggregateMatchIsotopeFilteredDataBody
         */
        export interface AggregateMatchIsotopeFilteredDataBody {
            /**
             * Target Ion Id
             * Filter targets by ID of the target ion
             */
            target_ion_id?: string;
            /**
             * Ion-specific filter parameters, used for match_score and sample_peak_area filtering, setting match_category
             */
            filter_params?: /* FilterParams */ FilterParams;
            /**
             * Include Match Interference
             * Include match interference data in the response
             */
            include_match_interference?: boolean;
        }
        /**
         * AggregateSampleMatchCompoundBody
         */
        export interface AggregateSampleMatchCompoundBody {
            /**
             * Target compound with required formula and optional name
             */
            target_compound: /* TargetCompoundMatches */ TargetCompoundMatches;
            filter_params?: /* FilterParams */ FilterParams;
        }
        /**
         * AggregateSampleMatchIonBody
         */
        export interface AggregateSampleMatchIonBody {
            /**
             * Target Ion Id
             * ID of the target ion
             */
            target_ion_id: string;
            /**
             * Target Collection Id
             * ID of the target collection to remove possible dublicates
             */
            target_collection_id: string;
            /**
             * Ion-specific filter parameters, used for match_score and sample_peak_area filtering
             */
            filter_params: /* FilterParams */ FilterParams;
        }
        /**
         * AttributeTemplateCreateBody
         */
        export interface AttributeTemplateCreateBody {
            /**
             * Name
             * Name of the attribute template
             */
            name: string;
            /**
             * Type
             * Type of the attribute template, e.g., 'sample_item'
             */
            type: string;
            /**
             * Template
             * List of template fields for the attribute template
             */
            template: /* TemplateField */ TemplateField[];
        }
        /**
         * AttributeTemplateUpdateBody
         */
        export interface AttributeTemplateUpdateBody {
            /**
             * Name
             * Name of the attribute template
             */
            name: string;
            /**
             * Type
             * Type of the attribute template, e.g., 'sample_item'
             */
            type: string;
            /**
             * Template
             * List of template fields for the attribute template
             */
            template: /* TemplateField */ TemplateField[];
        }
        /**
         * Body_auth_jwt_login_api_auth_login_post
         */
        export interface BodyAuthJwtLoginApiAuthLoginPost {
            /**
             * Grant Type
             */
            grant_type?: /* Grant Type */ string /* password */ | null;
            /**
             * Username
             */
            username: string;
            /**
             * Password
             */
            password: string;
            /**
             * Scope
             */
            scope?: string;
            /**
             * Client Id
             */
            client_id?: /* Client Id */ string | null;
            /**
             * Client Secret
             */
            client_secret?: /* Client Secret */ string | null;
        }
        /**
         * Body_get_target_isotopes_route_api_target_isotopes_get
         */
        export interface BodyGetTargetIsotopesRouteApiTargetIsotopesGet {
            /**
             * Target Compound Ids
             */
            target_compound_ids?: string[];
            /**
             * Ionization Mechanism Ids
             */
            ionization_mechanism_ids?: string[];
        }
        /**
         * Body_sample_file_upload_route_api_sample_files_upload_post
         */
        export interface BodySampleFileUploadRouteApiSampleFilesUploadPost {
            /**
             * File
             */
            file: string; // binary
        }
        /**
         * BuildParams
         */
        export interface BuildParams {
            /**
             * Calibration Collection
             * ID of the calibration collection
             */
            calibration_collection: string;
            /**
             * Ion Mechanisms
             * List of ionisation mechanism IDs for matching
             */
            ion_mechanisms: string[];
            /**
             * Calibration Ion Mechanisms
             * List of ionisation mechanism IDs for calibration
             */
            calibration_ion_mechanisms?: /**
             * Calibration Ion Mechanisms
             * List of ionisation mechanism IDs for calibration
             */
            string[] | null;
        }
        /**
         * CalibrationMzApplyBody
         */
        export interface CalibrationMzApplyBody {
            /**
             * Fit
             * Fit parameteres
             */
            fit: {
                [key: string]: any;
            };
        }
        /**
         * DeleteMatchCollectionsPayload
         */
        export interface DeleteMatchCollectionsPayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
            /**
             * Target Collections Ids
             * Optional list of target collection IDs to limit the match collections being deleted.
             */
            target_collections_ids?: /**
             * Target Collections Ids
             * Optional list of target collection IDs to limit the match collections being deleted.
             */
            string[] | null;
        }
        /**
         * DeleteMatchCompounsPayload
         */
        export interface DeleteMatchCompounsPayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
            /**
             * Target Compound Ids
             * Optional list of target compound IDs to limit the match compounds being deleted.
             */
            target_compound_ids?: /**
             * Target Compound Ids
             * Optional list of target compound IDs to limit the match compounds being deleted.
             */
            string[] | null;
        }
        /**
         * DeleteMatchInterferencesPayload
         */
        export interface DeleteMatchInterferencesPayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
            /**
             * Target Isotope Ids
             * Optional list of target isotope IDs to limit the match interferences being deleted.
             */
            target_isotope_ids?: /**
             * Target Isotope Ids
             * Optional list of target isotope IDs to limit the match interferences being deleted.
             */
            string[] | null;
        }
        /**
         * DeleteMatchIonsPayload
         */
        export interface DeleteMatchIonsPayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
            /**
             * Target Ion Ids
             * Optional list of target ion IDs to limit the match ions being deleted.
             */
            target_ion_ids?: /**
             * Target Ion Ids
             * Optional list of target ion IDs to limit the match ions being deleted.
             */
            string[] | null;
        }
        /**
         * DeleteMatchIsotopesPayload
         */
        export interface DeleteMatchIsotopesPayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
            /**
             * Target Isotope Ids
             * Optional list of target isotope IDs to limit the match isotopes being deleted.
             */
            target_isotope_ids?: /**
             * Target Isotope Ids
             * Optional list of target isotope IDs to limit the match isotopes being deleted.
             */
            string[] | null;
        }
        /**
         * Environment
         */
        export interface Environment {
            /**
             * Mz Calibration
             * m/z calibration data of the sample
             */
            mz_calibration: {
                [key: string]: any;
            };
        }
        /**
         * ErrorModel
         */
        export interface ErrorModel {
            /**
             * Detail
             */
            detail: /* Detail */ string | {
                [name: string]: string;
            };
        }
        /**
         * FilterParams
         */
        export interface FilterParams {
            /**
             * Mz Tolerance
             * Tolerance for mass-to-charge ratio (m/z) error.
             */
            mz_tolerance?: number;
            /**
             * Isotope Ratio Tolerance
             * Tolerance for the ratio of isotopic abundances.
             */
            isotope_ratio_tolerance?: number;
            /**
             * Peak Min Intensity
             * Minimum peak intensity threshold for considering a match.
             */
            peak_min_intensity?: number;
            /**
             * Min Isotope Abundance
             * Minimum relative abundance of isotopes to consider in the match.
             */
            min_isotope_abundance?: number;
            /**
             * Min Isotope Correlation
             * Minimum correlation of isotopic pattern required for a match.
             */
            min_isotope_correlation?: number;
            /**
             * Probable Match Threshold
             * Threshold score above which a match is considered probable.
             */
            probable_match_threshold?: number;
            /**
             * Possible Match Threshold
             * Threshold score above which a match is considered possible, but below the probable match threshold.
             */
            possible_match_threshold?: number;
        }
        /**
         * FilterSamplePayload
         */
        export interface FilterSamplePayload {
            /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * Filter samples by ID of the sample batch
             */
            string | null;
            /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            sample_item_id?: /**
             * Sample Item Id
             * Filter samples by ID of the sample item
             */
            string | null;
        }
        /**
         * GetSampleFilePeakTimeseriesBody
         */
        export interface GetSampleFilePeakTimeseriesBody {
            /**
             * Peak Mz
             */
            peak_mz: number;
            /**
             * Peak Mz Tolerance Ppm
             */
            peak_mz_tolerance_ppm?: /* Peak Mz Tolerance Ppm */ number | null;
        }
        /**
         * HTTPValidationError
         */
        export interface HTTPValidationError {
            /**
             * Detail
             */
            detail?: /* ValidationError */ ValidationError[];
        }
        /**
         * InstrumentFunctionCreateBody
         */
        export interface InstrumentFunctionCreateBody {
            /**
             * Instrument
             * Instrument name
             */
            instrument: string;
            /**
             * Method File
             * Name of the method file associated with the instrument function. Must start with the date in YYYYMMDD format.
             */
            method_file: string;
            /**
             * Datetime Utc
             * UTC timestamp from which onwards the specified instrument functions are applied, until new instrument functions are generated.
             */
            datetime_utc: string; // date-time
            /**
             * Peak shape data
             */
            peakshape: /* PeakShape */ PeakShape;
            /**
             * Resolution Function
             * Parameters defining the resolution function, which is used to scale the width of peaks accurately during peak fitting.
             */
            resolution_function: number[];
        }
        /**
         * IonizationMechanismCreate
         */
        export interface IonizationMechanismCreate {
            /**
             * Ionization Mechanism Polarity
             * Polarity of the ionization mechanism ('+' or '-')
             */
            ionization_mechanism_polarity: string;
            /**
             * Ionization Mechanism
             * Chemical formula modification (addition/abstraction) representing the ionized form.
             */
            ionization_mechanism: string;
            /**
             * Reagent
             * Reagent used in the ionization process, if applicable.
             */
            reagent?: /**
             * Reagent
             * Reagent used in the ionization process, if applicable.
             */
            string | null;
        }
        /**
         * IsotopeRating
         */
        export interface IsotopeRating {
            /**
             * Isotope Rating
             * Match isotope rating from 1 to 5
             */
            isotope_rating: number;
            /**
             * Target Isotope Id
             * ID of the associated target isotope
             */
            target_isotope_id: string;
        }
        /**
         * MatchCollectionBase
         */
        export interface MatchCollectionBase {
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Target Collection Id
             * Foreign key to target_collection
             */
            target_collection_id: string;
            /**
             * Match Score
             * Score of the match
             */
            match_score: number;
            /**
             * Match Category
             * Category of the match
             */
            match_category: number;
            /**
             * Sample Peak Area Sum
             * Sum of the area of the sample peak
             */
            sample_peak_area_sum: number;
            /**
             * Sample Peak Interference Sum
             * Sum of the area of the sample peak interference
             */
            sample_peak_interference_sum: number;
        }
        /**
         * MatchCompoundBase
         */
        export interface MatchCompoundBase {
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Target Compound Id
             * Foreign key to target_compound
             */
            target_compound_id: string;
            /**
             * Match Score
             * Score of the match
             */
            match_score: number;
            /**
             * Match Category
             * Category of the match
             */
            match_category: number;
            /**
             * Sample Peak Area Sum
             * Sum of the area of the sample peak
             */
            sample_peak_area_sum: number;
            /**
             * Sample Peak Interference Sum
             * Sum of the area of the sample peak interference
             */
            sample_peak_interference_sum: number;
        }
        /**
         * MatchComputeBody
         */
        export interface MatchComputeBody {
            /**
             * Added Target Compound Ids
             * List of target compound IDs to compute matches for
             */
            added_target_compound_ids?: /**
             * Added Target Compound Ids
             * List of target compound IDs to compute matches for
             */
            string[] | null;
            /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to compute matches for
             */
            added_ionization_mechanism_ids?: /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to compute matches for
             */
            string[] | null;
        }
        /**
         * MatchInterferenceBase
         */
        export interface MatchInterferenceBase {
            /**
             * Match Interference Id
             * ID of match interference, primary key
             */
            match_interference_id: string;
            /**
             * Target Isotope Id
             * Foreign key to target_isotope
             */
            target_isotope_id: string;
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Sample Peak Interference
             * Sample peak interference
             */
            sample_peak_interference: number;
        }
        /**
         * MatchIonBase
         */
        export interface MatchIonBase {
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Target Ion Id
             * Foreign key to target_ion
             */
            target_ion_id: string;
            /**
             * Match Score
             * Score of the match ion
             */
            match_score: number;
            /**
             * Match Category
             * Category of the match
             */
            match_category: number;
            /**
             * Sample Peak Area Sum
             * Area of the sample peak
             */
            sample_peak_area_sum: number;
            /**
             * Sample Peak Interference Sum
             * Area of the sample peak
             */
            sample_peak_interference_sum: number;
        }
        /**
         * MatchIsotopeBase
         */
        export interface MatchIsotopeBase {
            /**
             * Match Isotope Id
             * ID of match isotope, primary key
             */
            match_isotope_id: string;
            /**
             * Target Isotope Id
             * Foreign key to target_isotope
             */
            target_isotope_id: string;
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Sample Peak Id
             * ID of the sample peak
             */
            sample_peak_id: number;
            /**
             * Sample Peak Mz
             * Mass-to-charge ratio of the sample peak
             */
            sample_peak_mz: number;
            /**
             * Sample Peak Area
             * Area of the sample peak
             */
            sample_peak_area: number;
            /**
             * Sample Peak Area Relative
             * Relative area of the sample peak
             */
            sample_peak_area_relative: number;
            /**
             * Sample Peak Tof
             * Time-of-flight of the sample peak
             */
            sample_peak_tof: number;
            /**
             * Match Abundance Error
             * Abundance error of the match
             */
            match_abundance_error: number;
            /**
             * Match Mz Error
             * Mass-to-charge ratio error of the match
             */
            match_mz_error: number;
            /**
             * Match Isotope Correlation
             * Correlation of the isotope match
             */
            match_isotope_correlation: number;
            /**
             * Match Score
             * Score of the match
             */
            match_score: number;
        }
        /**
         * MatchRatingChecklist
         */
        export interface MatchRatingChecklist {
            /**
             * Isotopes Rating
             * List of match isotopes with data and rating
             */
            isotopes_rating: /* IsotopeRating */ IsotopeRating[];
            /**
             * Timeseries Good Match
             * Do the timeseries indicate a good match between the isotopes
             */
            timeseries_good_match: boolean;
            /**
             * Timeseries Expected Behavior
             * Do the timeseries indicate expected behavior? Where 0 - 'No', 1 - 'Maybe', 2 - 'Yes'
             */
            timeseries_expected_behavior: number;
            /**
             * Comment
             * Optional comment
             */
            comment?: /**
             * Comment
             * Optional comment
             */
            string | null;
        }
        /**
         * MatchRatingCreate
         */
        export interface MatchRatingCreate {
            /**
             * Sample Item Id
             * ID of the associated sample item
             */
            sample_item_id: string;
            /**
             * Target Ion Id
             * ID of the associated target ion
             */
            target_ion_id: string;
            /**
             * Rating
             * Rating value between 0 and 2
             */
            rating: number;
            /**
             * Checklist for the match rating
             */
            checklist?: /* Checklist for the match rating */ /* MatchRatingChecklist */ MatchRatingChecklist | null;
            /**
             * Environment-related data
             */
            environment: /* Environment */ Environment;
        }
        /**
         * MatchRemovePayload
         */
        export interface MatchRemovePayload {
            /**
             * Removed Target Compound Ids
             * Matches associated with isotopes derived from these compounds will be deleted.
             */
            removed_target_compound_ids?: /**
             * Removed Target Compound Ids
             * Matches associated with isotopes derived from these compounds will be deleted.
             */
            string[] | null;
            /**
             * Removed Ionization Mechanism Ids
             * Matches associated with isotopes generated by these ionization mechanisms will be deleted
             */
            removed_ionization_mechanism_ids?: /**
             * Removed Ionization Mechanism Ids
             * Matches associated with isotopes generated by these ionization mechanisms will be deleted
             */
            string[] | null;
        }
        /**
         * MatchSampleBase
         */
        export interface MatchSampleBase {
            /**
             * Sample Item Id
             * Foreign key to sample_item
             */
            sample_item_id: string;
            /**
             * Match Score
             * Score of the match
             */
            match_score: number;
            /**
             * Match Category
             * Category of the match
             */
            match_category: number;
            /**
             * Sample Peak Area Sum
             * Sum of the area of the sample peak
             */
            sample_peak_area_sum: number;
            /**
             * Sample Peak Interference Sum
             * Sum of the area of the sample peak interference
             */
            sample_peak_interference_sum: number;
        }
        /**
         * MzCalibrationParams
         */
        export interface MzCalibrationParams {
            /**
             * Match Score Min
             * Minimum match score
             */
            match_score_min?: number;
            /**
             * Refine Window
             * Refine window parameter
             */
            refine_window?: number;
            /**
             * Peak Intensity Min
             * Minimum peak intensity
             */
            peak_intensity_min?: number;
            /**
             * Isotope Abundance Min
             * Minimum isotope abundance
             */
            isotope_abundance_min?: number;
        }
        /**
         * PeakShape
         */
        export interface PeakShape {
            /**
             * X
             * X-axis values representing the mass-to-charge ratio (m/z) for the peak shape.
             */
            x: number[];
            /**
             * Y
             * Y-axis values representing intensity for each corresponding m/z value in the peak shape.
             */
            y: number[];
        }
        /**
         * RematchBatchBody
         */
        export interface RematchBatchBody {
            /**
             * Added Target Compound Ids
             * List of target compound IDs to add matches for
             */
            added_target_compound_ids?: /**
             * Added Target Compound Ids
             * List of target compound IDs to add matches for
             */
            string[] | null;
            /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to add matches for
             */
            added_ionization_mechanism_ids?: /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to add matches for
             */
            string[] | null;
            /**
             * Removed Target Compound Ids
             * List of target compound IDs to remove matches for
             */
            removed_target_compound_ids?: /**
             * Removed Target Compound Ids
             * List of target compound IDs to remove matches for
             */
            string[] | null;
            /**
             * Removed Ionization Mechanism Ids
             * List of ionization mechanism IDs to remove matches for
             */
            removed_ionization_mechanism_ids?: /**
             * Removed Ionization Mechanism Ids
             * List of ionization mechanism IDs to remove matches for
             */
            string[] | null;
            /**
             * Sample Batch Id
             * ID of the sample batch
             */
            sample_batch_id?: /**
             * Sample Batch Id
             * ID of the sample batch
             */
            string | null;
        }
        /**
         * RematchBatchesBody
         */
        export interface RematchBatchesBody {
            /**
             * Sample Batches
             * List of sample batches to rematch
             */
            sample_batches: /* RematchBatchBody */ RematchBatchBody[];
        }
        /**
         * RematchBody
         */
        export interface RematchBody {
            /**
             * Added Target Compound Ids
             * List of target compound IDs to add matches for
             */
            added_target_compound_ids?: /**
             * Added Target Compound Ids
             * List of target compound IDs to add matches for
             */
            string[] | null;
            /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to add matches for
             */
            added_ionization_mechanism_ids?: /**
             * Added Ionization Mechanism Ids
             * List of ionization mechanism IDs to add matches for
             */
            string[] | null;
            /**
             * Removed Target Compound Ids
             * List of target compound IDs to remove matches for
             */
            removed_target_compound_ids?: /**
             * Removed Target Compound Ids
             * List of target compound IDs to remove matches for
             */
            string[] | null;
            /**
             * Removed Ionization Mechanism Ids
             * List of ionization mechanism IDs to remove matches for
             */
            removed_ionization_mechanism_ids?: /**
             * Removed Ionization Mechanism Ids
             * List of ionization mechanism IDs to remove matches for
             */
            string[] | null;
        }
        /**
         * SampleBatchCopyBody
         */
        export interface SampleBatchCopyBody {
            /**
             * Workspace Id
             * ID of the workspace where to copy the batch
             */
            workspace_id: string;
            /**
             * Sample Batch Name
             * Name of the new sample batch
             */
            sample_batch_name: string;
            /**
             * Sample Batch Description
             * Description of the new sample batch
             */
            sample_batch_description?: /**
             * Sample Batch Description
             * Description of the new sample batch
             */
            string | null;
        }
        /**
         * SampleBatchCreateBody
         */
        export interface SampleBatchCreateBody {
            /**
             * Workspace Id
             * ID of the workspace associated with the sample batch
             */
            workspace_id: string;
            /**
             * Sample Batch Name
             * Name of the sample batch
             */
            sample_batch_name: string;
            /**
             * Sample Batch Description
             * Description of the sample batch
             */
            sample_batch_description?: /**
             * Sample Batch Description
             * Description of the sample batch
             */
            string | null;
            /**
             * Build parameters of the sample batch
             */
            build_params: /* BuildParams */ BuildParams;
            /**
             * Target Collection Ids
             * IDs of target collections associated with the sample batch
             */
            target_collection_ids: string[];
        }
        /**
         * SampleBatchImportSamplesBody
         */
        export interface SampleBatchImportSamplesBody {
            /**
             * Sample Items
             * Sample items to be created and imported to the sample batch
             */
            sample_items: /* SampleItemCreate */ SampleItemCreate[];
            mz_calibration_params?: /* MzCalibrationParams */ MzCalibrationParams;
            /**
             * Calibrate Batch
             * Flag to control whether the batch should be calibrated.
             */
            calibrate_batch?: boolean;
        }
        /**
         * SampleBatchUpdateBody
         */
        export interface SampleBatchUpdateBody {
            /**
             * Workspace Id
             * ID of the workspace associated with the sample batch
             */
            workspace_id: string;
            /**
             * Sample Batch Name
             * Name of the sample batch
             */
            sample_batch_name: string;
            /**
             * Sample Batch Description
             * Description of the sample batch
             */
            sample_batch_description?: /**
             * Sample Batch Description
             * Description of the sample batch
             */
            string | null;
            /**
             * Build parameters of the sample batch
             */
            build_params: /* BuildParams */ BuildParams;
            /**
             * Target Collection Ids
             * IDs of target collections associated with the sample batch
             */
            target_collection_ids: string[];
        }
        /**
         * SampleFileCreate
         */
        export interface SampleFileCreate {
            /**
             * Filename
             * Name of the sample file
             */
            filename: string;
            /**
             * Instrument
             * Instrument associated with the file
             */
            instrument: string;
            /**
             * Method File
             * Instrument method filename
             */
            method_file?: /**
             * Method File
             * Instrument method filename
             */
            string | null;
            /**
             * Datetime
             * Datetime (local) of creation of the sample file
             */
            datetime: string; // date-time
            /**
             * Datetime Utc
             * Datetime (UTC) of creation of the sample file
             */
            datetime_utc: string; // date-time
            /**
             * Length
             * Length of the sample file
             */
            length: number;
            /**
             * Range
             * m/z range of the sample file
             */
            range: number[];
            /**
             * Mz Calibration
             * m/z calibration function parameters of the sample file
             */
            mz_calibration?: /**
             * Mz Calibration
             * m/z calibration function parameters of the sample file
             */
            {
                [key: string]: any;
            } | null;
            /**
             * Tic
             * TIC of the sample file
             */
            tic: number;
            /**
             * Polarity
             * Polarity of the sample file
             */
            polarity: string;
        }
        /**
         * SampleFileUpdate
         */
        export interface SampleFileUpdate {
            /**
             * Filename
             * Name of the sample file
             */
            filename: string;
            /**
             * Instrument
             * Instrument associated with the file
             */
            instrument: string;
            /**
             * Datetime
             * Datetime (local) of creation of the sample file
             */
            datetime: string; // date-time
            /**
             * Datetime Utc
             * Datetime (UTC) of creation of the sample file
             */
            datetime_utc: string; // date-time
            /**
             * Length
             * Length of the sample file
             */
            length: number;
            /**
             * Range
             * m/z range of the sample file
             */
            range: number[];
            /**
             * Mz Calibration
             * m/z calibration function parameters of the sample file
             */
            mz_calibration: {
                [key: string]: any;
            };
            /**
             * Tic
             * TIC of the sample file
             */
            tic: number;
            /**
             * Polarity
             * Polarity of the sample file
             */
            polarity?: string;
        }
        /**
         * SampleItemCopyBody
         */
        export interface SampleItemCopyBody {
            /**
             * Sample Batch Id
             * ID of the sample batch where to copy sample item
             */
            sample_batch_id: string;
            /**
             * Sample Item Name
             * Name of the new sample item
             */
            sample_item_name: string;
        }
        /**
         * SampleItemCreate
         */
        export interface SampleItemCreate {
            /**
             * Sample Batch Id
             * ID of the associated sample batch
             */
            sample_batch_id: string;
            /**
             * Filename
             * Name of the sample file
             */
            filename: string;
            /**
             * Sample Item Name
             * Name of the sample item
             */
            sample_item_name: string;
            /**
             * Sample Item Type
             * Type of the sample item
             */
            sample_item_type: string;
            /**
             * Sample Item Attributes
             * Attributes of the sample item
             */
            sample_item_attributes: {
                [key: string]: any;
            };
            /**
             * Filter Id
             * Filter ID of the sample item
             */
            filter_id?: /**
             * Filter Id
             * Filter ID of the sample item
             */
            string | null;
        }
        /**
         * SampleItemProcessBody
         */
        export interface SampleItemProcessBody {
            /**
             * Sample item to be processed (created, calibrated, matched)
             */
            sample_item: /* SampleItemCreate */ SampleItemCreate;
            mz_calibration_params?: /* MzCalibrationParams */ MzCalibrationParams;
        }
        /**
         * SampleItemUpdate
         */
        export interface SampleItemUpdate {
            /**
             * Sample Batch Id
             * ID of the associated sample batch
             */
            sample_batch_id: string;
            /**
             * Filename
             * Name of the sample file
             */
            filename: string;
            /**
             * Sample Item Name
             * Name of the sample item
             */
            sample_item_name: string;
            /**
             * Sample Item Type
             * Type of the sample item
             */
            sample_item_type: string;
            /**
             * Sample Item Attributes
             * Attributes of the sample item
             */
            sample_item_attributes: {
                [key: string]: any;
            };
            /**
             * Filter Id
             * Filter ID of the sample item
             */
            filter_id?: /**
             * Filter Id
             * Filter ID of the sample item
             */
            string | null;
        }
        /**
         * TargetCollectionCreateBody
         */
        export interface TargetCollectionCreateBody {
            /**
             * Target Collection Name
             * Name of the target collection
             */
            target_collection_name: string;
            /**
             * Target Collection Description
             * Description of the target collection
             */
            target_collection_description?: /**
             * Target Collection Description
             * Description of the target collection
             */
            string | null;
            /**
             * Target Collection Type
             * Type of the target collection
             */
            target_collection_type: string;
            /**
             * Target Compounds Create
             * Compounds to be created and added to the target collection
             */
            target_compounds_create?: /**
             * Target Compounds Create
             * Compounds to be created and added to the target collection
             */
            /* TargetCompoundBase */ TargetCompoundBase[] | null;
            /**
             * Target Compound Ids
             * IDs of already existing in DB target compounds to be associated with the target collection
             */
            target_compound_ids?: /**
             * Target Compound Ids
             * IDs of already existing in DB target compounds to be associated with the target collection
             */
            string[] | null;
            /**
             * Sample Batch Ids
             * IDs of sample batches where to add the new target collection
             */
            sample_batch_ids?: /**
             * Sample Batch Ids
             * IDs of sample batches where to add the new target collection
             */
            string[] | null;
        }
        /**
         * TargetCollectionUpdateBody
         */
        export interface TargetCollectionUpdateBody {
            /**
             * Target Collection Name
             * Name of the target collection
             */
            target_collection_name: string;
            /**
             * Target Collection Description
             * Description of the target collection
             */
            target_collection_description?: /**
             * Target Collection Description
             * Description of the target collection
             */
            string | null;
            /**
             * Target Collection Type
             * Type of the target collection
             */
            target_collection_type: string;
            /**
             * Target Compound Ids
             * IDs of already existing in db target compounds to be associated with the target collection
             */
            target_compound_ids?: /**
             * Target Compound Ids
             * IDs of already existing in db target compounds to be associated with the target collection
             */
            string[] | null;
            /**
             * Target Compounds Create
             * Compounds to be created and added to the target collection
             */
            target_compounds_create?: /**
             * Target Compounds Create
             * Compounds to be created and added to the target collection
             */
            /* TargetCompoundBase */ TargetCompoundBase[] | null;
            /**
             * Sample Batch Ids
             * IDs of sample batches associated with the target collection
             */
            sample_batch_ids?: /**
             * Sample Batch Ids
             * IDs of sample batches associated with the target collection
             */
            string[] | null;
        }
        /**
         * TargetCompoundBase
         */
        export interface TargetCompoundBase {
            /**
             * Target Compound Id
             * ID of the target compound
             */
            target_compound_id?: /**
             * Target Compound Id
             * ID of the target compound
             */
            string | null;
            /**
             * Target Compound Name
             * Name of the target compound
             */
            target_compound_name?: /**
             * Target Compound Name
             * Name of the target compound
             */
            string | null;
            /**
             * Target Compound Formula
             * Formula of the target compound
             */
            target_compound_formula: string;
            /**
             * Cas Number
             * CAS Number of the target compound
             */
            cas_number?: /**
             * Cas Number
             * CAS Number of the target compound
             */
            string | null;
        }
        /**
         * TargetCompoundMatches
         */
        export interface TargetCompoundMatches {
            /**
             * Target Compound Id
             * ID of the target compound
             */
            target_compound_id?: /**
             * Target Compound Id
             * ID of the target compound
             */
            string | null;
            /**
             * Target Compound Name
             * Name of the target compound
             */
            target_compound_name?: /**
             * Target Compound Name
             * Name of the target compound
             */
            string | null;
            /**
             * Target Compound Formula
             * Formula of the target compound
             */
            target_compound_formula: string;
            /**
             * Cas Number
             * CAS Number of the target compound
             */
            cas_number?: /**
             * Cas Number
             * CAS Number of the target compound
             */
            string | null;
        }
        /**
         * TargetCompoundUpdate
         */
        export interface TargetCompoundUpdate {
            /**
             * Target Compound Id
             * ID of the target compound
             */
            target_compound_id: string;
            /**
             * Target Collection Id
             * ID of the target collection
             */
            target_collection_id?: /**
             * Target Collection Id
             * ID of the target collection
             */
            string | null;
            /**
             * Target Compound Name
             * Name of the target compound
             */
            target_compound_name?: /**
             * Target Compound Name
             * Name of the target compound
             */
            string | null;
            /**
             * Target Compound Formula
             * Formula of the target compound
             */
            target_compound_formula?: /**
             * Target Compound Formula
             * Formula of the target compound
             */
            string | null;
            /**
             * Cas Number
             * CAS Number of the target compound
             */
            cas_number?: /**
             * Cas Number
             * CAS Number of the target compound
             */
            string | null;
        }
        /**
         * TargetIonUpdate
         */
        export interface TargetIonUpdate {
            /**
             * Filter Params
             * Ion-specific filter parameters
             */
            filter_params?: {
                [name: string]: /* FilterParams */ FilterParams;
            };
            /**
             * Delete Instrument Filters
             * Instrument name which filter parameteres to delete
             */
            delete_instrument_filters?: /**
             * Delete Instrument Filters
             * Instrument name which filter parameteres to delete
             */
            string | null;
        }
        /**
         * TemplateField
         */
        export interface TemplateField {
            /**
             * Label
             * Label of the template field
             */
            label: string;
            /**
             * Required
             * Indicates if the field is required
             */
            required?: /**
             * Required
             * Indicates if the field is required
             */
            boolean | null;
            /**
             * Value
             * Default value for the template field
             */
            value?: /**
             * Value
             * Default value for the template field
             */
            string | null;
        }
        /**
         * UserCreate
         * Schema for creating a new user. Provides fields required for user registration.
         */
        export interface UserCreate {
            /**
             * Email
             * User's email address. This will be used as the login credential.
             */
            email: string; // email
            /**
             * Password
             * User's password for authentication. Will be hashed upon creation.
             */
            password: string;
            /**
             * Is Active
             * Sets whether the user account is active upon creation.
             */
            is_active?: /**
             * Is Active
             * Sets whether the user account is active upon creation.
             */
            boolean | null;
            /**
             * Is Superuser
             * Specifies if the user will have superuser privileges upon creation.
             */
            is_superuser?: /**
             * Is Superuser
             * Specifies if the user will have superuser privileges upon creation.
             */
            boolean | null;
            /**
             * Is Verified
             * Specifies whether the user's email is verified.
             */
            is_verified?: /**
             * Is Verified
             * Specifies whether the user's email is verified.
             */
            boolean | null;
            /**
             * Username
             * Username for display purposes. Note: This is not used for login.
             */
            username: string;
            /**
             * Role Id
             * Role ID assigned to the user (e.g., '1' for regular users).
             */
            role_id?: number;
        }
        /**
         * UserRead
         * Schema to read user data, typically used in responses to provide user details.
         */
        export interface UserRead {
            /**
             * Id
             * Unique identifier of the user (Primary Key).
             */
            id: number;
            /**
             * Email
             * User's email address. This is used as the unique login credential in the authentication flow. Although the specs of OAuth2 login form refers to this as `username`, it actually expects the user's email address here for authentication.
             */
            email: string; // email
            /**
             * Is Active
             * Indicates if the user account is active and can log in.
             */
            is_active: boolean;
            /**
             * Is Superuser
             * Designates whether the user has superuser privileges.
             */
            is_superuser: boolean;
            /**
             * Is Verified
             * Indicates whether the user's email is verified.
             */
            is_verified: boolean;
            /**
             * Username
             * Name of the user, used for display purposes (not for login).
             */
            username: string;
            /**
             * Role Id
             * Role identifier of the user, linked to user role permissions.
             */
            role_id: number;
            /**
             * Registered At
             * Timestamp indicating when the user registered.
             */
            registered_at: string; // date-time
        }
        /**
         * UserUpdate
         * Schema for updating existing user information. Fields can be partially updated.
         */
        export interface UserUpdate {
            /**
             * Password
             * New password for the user. If not provided, the password remains unchanged.
             */
            password?: /**
             * Password
             * New password for the user. If not provided, the password remains unchanged.
             */
            string | null;
            /**
             * Email
             * Updated email address. If not provided, the current email remains unchanged.
             */
            email?: /**
             * Email
             * Updated email address. If not provided, the current email remains unchanged.
             */
            string /* email */ | null;
            /**
             * Is Active
             * Set to True or False to activate or deactivate the user account.
             */
            is_active?: /**
             * Is Active
             * Set to True or False to activate or deactivate the user account.
             */
            boolean | null;
            /**
             * Is Superuser
             * Set to True to grant or revoke superuser privileges.
             */
            is_superuser?: /**
             * Is Superuser
             * Set to True to grant or revoke superuser privileges.
             */
            boolean | null;
            /**
             * Is Verified
             * Set to True or False to mark the user as verified or not.
             */
            is_verified?: /**
             * Is Verified
             * Set to True or False to mark the user as verified or not.
             */
            boolean | null;
            /**
             * Username
             * Updated username for display purposes. Note: This is not used for login.
             */
            username?: /**
             * Username
             * Updated username for display purposes. Note: This is not used for login.
             */
            string | null;
            /**
             * Role Id
             * Updated role ID to assign a new role to the user.
             */
            role_id?: /**
             * Role Id
             * Updated role ID to assign a new role to the user.
             */
            number | null;
        }
        /**
         * ValidationError
         */
        export interface ValidationError {
            /**
             * Location
             */
            loc: (string | number)[];
            /**
             * Message
             */
            msg: string;
            /**
             * Error Type
             */
            type: string;
        }
        /**
         * WorkspaceCreate
         */
        export interface WorkspaceCreate {
            /**
             * Workspace Name
             * Name of the workspace
             */
            workspace_name: string;
            /**
             * Workspace Description
             * Description of the workspace
             */
            workspace_description?: /**
             * Workspace Description
             * Description of the workspace
             */
            string | null;
        }
        /**
         * WorkspaceUpdate
         */
        export interface WorkspaceUpdate {
            /**
             * Workspace Name
             * Name of the workspace
             */
            workspace_name?: /**
             * Workspace Name
             * Name of the workspace
             */
            string | null;
            /**
             * Workspace Description
             * Description of the workspace
             */
            workspace_description?: /**
             * Workspace Description
             * Description of the workspace
             */
            string | null;
        }
    }
}
declare namespace Paths {
    namespace AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* AggregateAndCreateMatchesBody */ Components.Schemas.AggregateAndCreateMatchesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* AggregateAndCreateMatchesBody */ Components.Schemas.AggregateAndCreateMatchesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* AggregateAndCreateMatchesBody */ Components.Schemas.AggregateAndCreateMatchesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* AggregateMatchIsotopeFilteredDataBody */ Components.Schemas.AggregateMatchIsotopeFilteredDataBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* AggregateMatchIsotopeFilteredDataBody */ Components.Schemas.AggregateMatchIsotopeFilteredDataBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* AggregateSampleMatchCompoundBody */ Components.Schemas.AggregateSampleMatchCompoundBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* AggregateSampleMatchIonBody */ Components.Schemas.AggregateSampleMatchIonBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* AggregateMatchIsotopeFilteredDataBody */ Components.Schemas.AggregateMatchIsotopeFilteredDataBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* AggregateMatchIsotopeFilteredDataBody */ Components.Schemas.AggregateMatchIsotopeFilteredDataBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AuthJwtLoginApiAuthLoginPost {
        export type RequestBody = /* Body_auth_jwt_login_api_auth_login_post */ Components.Schemas.BodyAuthJwtLoginApiAuthLoginPost;
        namespace Responses {
            export type $200 = any;
            export interface $204 {
            }
            export type $400 = /* ErrorModel */ Components.Schemas.ErrorModel;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace AuthJwtLogoutApiAuthLogoutPost {
        namespace Responses {
            export type $200 = any;
            export interface $204 {
            }
            export interface $401 {
            }
        }
    }
    namespace CalibrationMzApplyRouteApiCalibrationMzApplyPost {
        namespace Parameters {
            /**
             * Filename
             * The filename to aply m/z fit
             */
            export type Filename = string;
        }
        export interface QueryParameters {
            filename: /**
             * Filename
             * The filename to aply m/z fit
             */
            Parameters.Filename;
        }
        export type RequestBody = /* CalibrationMzApplyBody */ Components.Schemas.CalibrationMzApplyBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* MzCalibrationParams */ Components.Schemas.MzCalibrationParams;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* MzCalibrationParams */ Components.Schemas.MzCalibrationParams;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CalibrationMzFitRouteApiCalibrationMzFitPost {
        namespace Parameters {
            /**
             * Sample Item Id
             * The sample item ID to query for sample mz_calibration
             */
            export type SampleItemId = string;
        }
        export interface QueryParameters {
            sample_item_id: /**
             * Sample Item Id
             * The sample item ID to query for sample mz_calibration
             */
            Parameters.SampleItemId;
        }
        export type RequestBody = /* MzCalibrationParams */ Components.Schemas.MzCalibrationParams;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace ComputeAllSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksComputeGet {
        namespace Parameters {
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* SampleBatchCopyBody */ Components.Schemas.SampleBatchCopyBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* SampleItemCopyBody */ Components.Schemas.SampleItemCopyBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateAttributeTemplateRouteApiAttributeTemplatesPost {
        export type RequestBody = /* AttributeTemplateCreateBody */ Components.Schemas.AttributeTemplateCreateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateInstrumentFunctionRouteApiInstrumentFunctionsPost {
        export type RequestBody = /* InstrumentFunctionCreateBody */ Components.Schemas.InstrumentFunctionCreateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateIonizationMechanismRouteApiIonizationMechanismsPost {
        export type RequestBody = /* IonizationMechanismCreate */ Components.Schemas.IonizationMechanismCreate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchCollectionsRouteApiMatchCollectionsPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchCollectionBase */ Components.Schemas.MatchCollectionBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchCompoundsRouteApiMatchCompoundsPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchCompoundBase */ Components.Schemas.MatchCompoundBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchInterferencesRouteApiMatchInterferencesPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchInterferenceBase */ Components.Schemas.MatchInterferenceBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchIonsRouteApiMatchIonsPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchIonBase */ Components.Schemas.MatchIonBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchIsotopesRouteApiMatchIsotopesPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchIsotopeBase */ Components.Schemas.MatchIsotopeBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchRatingRouteApiMatchRatingsPost {
        export type RequestBody = /* MatchRatingCreate */ Components.Schemas.MatchRatingCreate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateMatchSamplesRouteApiMatchSamplesPost {
        /**
         * Body
         */
        export type RequestBody = /* MatchSampleBase */ Components.Schemas.MatchSampleBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateSampleBatchRouteApiSampleBatchesPost {
        export type RequestBody = /* SampleBatchCreateBody */ Components.Schemas.SampleBatchCreateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateSampleFileRouteApiSampleFilesPost {
        export type RequestBody = /* SampleFileCreate */ Components.Schemas.SampleFileCreate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateSampleItemRouteApiSampleItemsPost {
        export type RequestBody = /* SampleItemCreate */ Components.Schemas.SampleItemCreate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateTargetCollectionRouteApiTargetCollectionsPost {
        export type RequestBody = /* TargetCollectionCreateBody */ Components.Schemas.TargetCollectionCreateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateTargetCompoundsRouteApiTargetCompoundsPost {
        /**
         * Target Compounds
         */
        export type RequestBody = /* TargetCompoundBase */ Components.Schemas.TargetCompoundBase[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace CreateWorkspaceRouteApiWorkspacesPost {
        export type RequestBody = /* WorkspaceCreate */ Components.Schemas.WorkspaceCreate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdDelete {
        namespace Parameters {
            /**
             * Attribute Template Id
             */
            export type AttributeTemplateId = string;
        }
        export interface PathParameters {
            attribute_template_id: /* Attribute Template Id */ Parameters.AttributeTemplateId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteInstrumentFunctionRouteApiInstrumentFunctionsInstrumentFunctionIdDelete {
        namespace Parameters {
            /**
             * Instrument Function Id
             */
            export type InstrumentFunctionId = string;
        }
        export interface PathParameters {
            instrument_function_id: /* Instrument Function Id */ Parameters.InstrumentFunctionId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdDelete {
        namespace Parameters {
            /**
             * Ionization Mechanism Id
             */
            export type IonizationMechanismId = string;
        }
        export interface PathParameters {
            ionization_mechanism_id: /* Ionization Mechanism Id */ Parameters.IonizationMechanismId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchCollectionsRouteApiMatchCollectionsDelete {
        export type RequestBody = /* DeleteMatchCollectionsPayload */ Components.Schemas.DeleteMatchCollectionsPayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchCompoundsRouteApiMatchCompoundsDelete {
        export type RequestBody = /* DeleteMatchCompounsPayload */ Components.Schemas.DeleteMatchCompounsPayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchInterferencesRouteApiMatchInterferencesDelete {
        export type RequestBody = /* DeleteMatchInterferencesPayload */ Components.Schemas.DeleteMatchInterferencesPayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchIonsRouteApiMatchIonsDelete {
        export type RequestBody = /* DeleteMatchIonsPayload */ Components.Schemas.DeleteMatchIonsPayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchIsotopesRouteApiMatchIsotopesDelete {
        export type RequestBody = /* DeleteMatchIsotopesPayload */ Components.Schemas.DeleteMatchIsotopesPayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteMatchSamplesRouteApiMatchSamplesDelete {
        export type RequestBody = /* FilterSamplePayload */ Components.Schemas.FilterSamplePayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteSampleBatchRouteApiSampleBatchesSampleBatchIdDelete {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteSampleFileRouteApiSampleFilesSampleFileIdDelete {
        namespace Parameters {
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteSampleItemRouteApiSampleItemsSampleItemIdDelete {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete {
        namespace Parameters {
            /**
             * Delete Orphan Compounds
             * Delete orphan compounds associated with the target collection
             */
            export type DeleteOrphanCompounds = boolean;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = string;
        }
        export interface PathParameters {
            target_collection_id: /* Target Collection Id */ Parameters.TargetCollectionId;
        }
        export interface QueryParameters {
            delete_orphan_compounds?: /**
             * Delete Orphan Compounds
             * Delete orphan compounds associated with the target collection
             */
            Parameters.DeleteOrphanCompounds;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteTargetCompoundRouteApiTargetCompoundsTargetCompoundIdDelete {
        namespace Parameters {
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = string;
        }
        export interface PathParameters {
            target_compound_id: /* Target Compound Id */ Parameters.TargetCompoundId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace DeleteWorkspaceRouteApiWorkspacesWorkspaceIdDelete {
        namespace Parameters {
            /**
             * Workspace Id
             */
            export type WorkspaceId = string;
        }
        export interface PathParameters {
            workspace_id: /* Workspace Id */ Parameters.WorkspaceId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetAllMatchCompoundsRouteApiMatchCompoundsGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Match Category Min
             */
            export type MatchCategoryMin = /* Match Category Min */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Show Target Collection
             */
            export type ShowTargetCollection = boolean;
            /**
             * Show Target Compound
             */
            export type ShowTargetCompound = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = /* Target Compound Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_compound_id?: /* Target Compound Id */ Parameters.TargetCompoundId;
            match_category_min?: /* Match Category Min */ Parameters.MatchCategoryMin;
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
            show_target_collection?: /* Show Target Collection */ Parameters.ShowTargetCollection;
            show_target_compound?: /* Show Target Compound */ Parameters.ShowTargetCompound;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdGet {
        namespace Parameters {
            /**
             * Attribute Template Id
             */
            export type AttributeTemplateId = string;
        }
        export interface PathParameters {
            attribute_template_id: /* Attribute Template Id */ Parameters.AttributeTemplateId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetAttributeTemplatesRouteApiAttributeTemplatesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetBatchAndAggregatedMatchesRouteApiMatchAggregateBatchSampleBatchIdAllGet {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetBatchDataRouteApiMatchTargetsBatchSampleBatchIdGet {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export interface QueryParameters {
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetInstrumentFunctionRouteApiInstrumentFunctionsGet {
        namespace Parameters {
            /**
             * Filename
             */
            export type Filename = /* Filename */ string | null;
            /**
             * Instrument Function Id
             */
            export type InstrumentFunctionId = /* Instrument Function Id */ string | null;
        }
        export interface QueryParameters {
            filename?: /* Filename */ Parameters.Filename;
            instrument_function_id?: /* Instrument Function Id */ Parameters.InstrumentFunctionId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetInstrumentFunctionsRouteApiInstrumentFunctionsGet {
        namespace Parameters {
            /**
             * Instrument
             */
            export type Instrument = /* Instrument */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Method File
             */
            export type MethodFile = /* Method File */ string | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            instrument?: /* Instrument */ Parameters.Instrument;
            method_file?: /* Method File */ Parameters.MethodFile;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdGet {
        namespace Parameters {
            /**
             * Ionization Mechanism Id
             */
            export type IonizationMechanismId = string;
        }
        export interface PathParameters {
            ionization_mechanism_id: /* Ionization Mechanism Id */ Parameters.IonizationMechanismId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetIonizationMechanismsRouteApiIonizationMechanismsGet {
        namespace Parameters {
            /**
             * Ionization Mechanism
             */
            export type IonizationMechanism = /* Ionization Mechanism */ string | null;
            /**
             * Ionization Mechanism Polarity
             */
            export type IonizationMechanismPolarity = /* Ionization Mechanism Polarity */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Reagent
             */
            export type Reagent = /* Reagent */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            ionization_mechanism_polarity?: /* Ionization Mechanism Polarity */ Parameters.IonizationMechanismPolarity;
            ionization_mechanism?: /* Ionization Mechanism */ Parameters.IonizationMechanism;
            reagent?: /* Reagent */ Parameters.Reagent;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = /* Target Compound Id */ string | null;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            target_compound_id?: /* Target Compound Id */ Parameters.TargetCompoundId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Min Relative Abundance
             */
            export type MinRelativeAbundance = /* Min Relative Abundance */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Ion Id
             */
            export type TargetIonId = /* Target Ion Id */ string | null;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            target_ion_id?: /* Target Ion Id */ Parameters.TargetIonId;
            min_relative_abundance?: /* Min Relative Abundance */ Parameters.MinRelativeAbundance;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchCollectionRouteApiMatchCollectionsMatchCollectionIdGet {
        namespace Parameters {
            /**
             * Match Collection Id
             */
            export type MatchCollectionId = string;
        }
        export interface PathParameters {
            match_collection_id: /* Match Collection Id */ Parameters.MatchCollectionId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchCollectionsRouteApiMatchCollectionsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Match Category Min
             */
            export type MatchCategoryMin = /* Match Category Min */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            match_category_min?: /* Match Category Min */ Parameters.MatchCategoryMin;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchCompoundRouteApiMatchCompoundsMatchCompoundIdGet {
        namespace Parameters {
            /**
             * Match Compound Id
             */
            export type MatchCompoundId = string;
        }
        export interface PathParameters {
            match_compound_id: /* Match Compound Id */ Parameters.MatchCompoundId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchInterferenceRouteApiMatchInterferencesMatchInterferenceIdGet {
        namespace Parameters {
            /**
             * Match Interference Id
             */
            export type MatchInterferenceId = string;
        }
        export interface PathParameters {
            match_interference_id: /* Match Interference Id */ Parameters.MatchInterferenceId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchInterferencesRouteApiMatchInterferencesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Max Sample Peak Interference
             */
            export type MaxSamplePeakInterference = /* Max Sample Peak Interference */ number | null;
            /**
             * Min Sample Peak Interference
             */
            export type MinSamplePeakInterference = /* Min Sample Peak Interference */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Isotope Id
             */
            export type TargetIsotopeId = /* Target Isotope Id */ string | null;
        }
        export interface QueryParameters {
            target_isotope_id?: /* Target Isotope Id */ Parameters.TargetIsotopeId;
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            min_sample_peak_interference?: /* Min Sample Peak Interference */ Parameters.MinSamplePeakInterference;
            max_sample_peak_interference?: /* Max Sample Peak Interference */ Parameters.MaxSamplePeakInterference;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchIonRouteApiMatchIonsMatchIonIdGet {
        namespace Parameters {
            /**
             * Match Ion Id
             */
            export type MatchIonId = string;
        }
        export interface PathParameters {
            match_ion_id: /* Match Ion Id */ Parameters.MatchIonId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchIonsRouteApiMatchIonsGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Ionization Mechanism Id
             */
            export type IonizationMechanismId = /* Ionization Mechanism Id */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Match Category Min
             */
            export type MatchCategoryMin = /* Match Category Min */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Show Ionization Mechanism
             */
            export type ShowIonizationMechanism = boolean;
            /**
             * Show Target Collection
             */
            export type ShowTargetCollection = boolean;
            /**
             * Show Target Compound
             */
            export type ShowTargetCompound = boolean;
            /**
             * Show Target Ion
             */
            export type ShowTargetIon = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Ion Id
             */
            export type TargetIonId = /* Target Ion Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_ion_id?: /* Target Ion Id */ Parameters.TargetIonId;
            ionization_mechanism_id?: /* Ionization Mechanism Id */ Parameters.IonizationMechanismId;
            match_category_min?: /* Match Category Min */ Parameters.MatchCategoryMin;
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
            show_target_collection?: /* Show Target Collection */ Parameters.ShowTargetCollection;
            show_target_compound?: /* Show Target Compound */ Parameters.ShowTargetCompound;
            show_target_ion?: /* Show Target Ion */ Parameters.ShowTargetIon;
            show_ionization_mechanism?: /* Show Ionization Mechanism */ Parameters.ShowIonizationMechanism;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchIsotopeRouteApiMatchIsotopesMatchIsotopeIdGet {
        namespace Parameters {
            /**
             * Match Isotope Id
             */
            export type MatchIsotopeId = string;
        }
        export interface PathParameters {
            match_isotope_id: /* Match Isotope Id */ Parameters.MatchIsotopeId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchIsotopesRouteApiMatchIsotopesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Show Target Isotope
             */
            export type ShowTargetIsotope = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Isotope Id
             */
            export type TargetIsotopeId = /* Target Isotope Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_isotope_id?: /* Target Isotope Id */ Parameters.TargetIsotopeId;
            show_target_isotope?: /* Show Target Isotope */ Parameters.ShowTargetIsotope;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchRatingRouteApiMatchRatingsMatchRatingIdGet {
        namespace Parameters {
            /**
             * Match Rating Id
             */
            export type MatchRatingId = string;
        }
        export interface PathParameters {
            match_rating_id: /* Match Rating Id */ Parameters.MatchRatingId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchRatingsRouteApiMatchRatingsGet {
        namespace Parameters {
            /**
             * Datetime Max
             */
            export type DatetimeMax = /* Datetime Max */ string /* date-time */ | null;
            /**
             * Datetime Min
             */
            export type DatetimeMin = /* Datetime Min */ string /* date-time */ | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Rating
             */
            export type Rating = /* Rating */ number | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Ion Id
             */
            export type TargetIonId = /* Target Ion Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            target_ion_id?: /* Target Ion Id */ Parameters.TargetIonId;
            rating?: /* Rating */ Parameters.Rating;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            datetime_min?: /* Datetime Min */ Parameters.DatetimeMin;
            datetime_max?: /* Datetime Max */ Parameters.DatetimeMax;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = /* Target Compound Id */ string | null;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
            target_compound_id?: /* Target Compound Id */ Parameters.TargetCompoundId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet {
        namespace Parameters {
            /**
             * Deduplicate
             */
            export type Deduplicate = /* Deduplicate */ boolean | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Min Relative Abundance
             */
            export type MinRelativeAbundance = /* Min Relative Abundance */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Ion Id
             */
            export type TargetIonId = /* Target Ion Id */ string | null;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export interface QueryParameters {
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            deduplicate?: /* Deduplicate */ Parameters.Deduplicate;
            target_ion_id?: /* Target Ion Id */ Parameters.TargetIonId;
            min_relative_abundance?: /* Min Relative Abundance */ Parameters.MinRelativeAbundance;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSampleRouteApiMatchSamplesMatchSampleIdGet {
        namespace Parameters {
            /**
             * Match Sample Id
             */
            export type MatchSampleId = string;
        }
        export interface PathParameters {
            match_sample_id: /* Match Sample Id */ Parameters.MatchSampleId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetMatchSamplesRouteApiMatchSamplesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Match Category Min
             */
            export type MatchCategoryMin = /* Match Category Min */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            match_category_min?: /* Match Category Min */ Parameters.MatchCategoryMin;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetRecentSampleFilesRouteApiSampleFilesRecentGet {
        namespace Parameters {
            /**
             * Datetime Max
             */
            export type DatetimeMax = /* Datetime Max */ string /* date-time */ | null;
            /**
             * Datetime Min
             */
            export type DatetimeMin = /* Datetime Min */ string /* date-time */ | null;
            /**
             * Days
             */
            export type Days = number;
            /**
             * Filename
             */
            export type Filename = /* Filename */ string | null;
            /**
             * Instrument
             */
            export type Instrument = /* Instrument */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            datetime_min?: /* Datetime Min */ Parameters.DatetimeMin;
            datetime_max?: /* Datetime Max */ Parameters.DatetimeMax;
            instrument?: /* Instrument */ Parameters.Instrument;
            filename?: /* Filename */ Parameters.Filename;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
            days?: /* Days */ Parameters.Days;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleAggregateMatchesRouteApiMatchAggregateSampleSampleItemIdAllGet {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleBatchRouteApiSampleBatchesSampleBatchIdGet {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleBatchesRouteApiSampleBatchesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Workspace Id
             */
            export type WorkspaceId = /* Workspace Id */ string | null;
        }
        export interface QueryParameters {
            workspace_id?: /* Workspace Id */ Parameters.WorkspaceId;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost {
        namespace Parameters {
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        export type RequestBody = /* GetSampleFilePeakTimeseriesBody */ Components.Schemas.GetSampleFilePeakTimeseriesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet {
        namespace Parameters {
            /**
             * Areas
             */
            export type Areas = boolean;
            /**
             * Heights
             */
            export type Heights = boolean;
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        export interface QueryParameters {
            areas?: /* Areas */ Parameters.Areas;
            heights?: /* Heights */ Parameters.Heights;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleFileRouteApiSampleFilesSampleFileIdGet {
        namespace Parameters {
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet {
        namespace Parameters {
            /**
             * Mz Max
             */
            export type MzMax = /* Mz Max */ number | null;
            /**
             * Mz Min
             */
            export type MzMin = /* Mz Min */ number | null;
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
            /**
             * T Max
             */
            export type TMax = /* T Max */ number | null;
            /**
             * T Min
             */
            export type TMin = /* T Min */ number | null;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        export interface QueryParameters {
            t_min?: /* T Min */ Parameters.TMin;
            t_max?: /* T Max */ Parameters.TMax;
            mz_min?: /* Mz Min */ Parameters.MzMin;
            mz_max?: /* Mz Max */ Parameters.MzMax;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleFilesRouteApiSampleFilesGet {
        namespace Parameters {
            /**
             * Datetime Max
             */
            export type DatetimeMax = /* Datetime Max */ string /* date-time */ | null;
            /**
             * Datetime Min
             */
            export type DatetimeMin = /* Datetime Min */ string /* date-time */ | null;
            /**
             * Filename
             */
            export type Filename = /* Filename */ string | null;
            /**
             * Instrument
             */
            export type Instrument = /* Instrument */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            datetime_min?: /* Datetime Min */ Parameters.DatetimeMin;
            datetime_max?: /* Datetime Max */ Parameters.DatetimeMax;
            instrument?: /* Instrument */ Parameters.Instrument;
            filename?: /* Filename */ Parameters.Filename;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleItemRouteApiSampleItemsSampleItemIdGet {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleItemsRouteApiSampleItemsGet {
        namespace Parameters {
            /**
             * Filename
             */
            export type Filename = /* Filename */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            filename?: /* Filename */ Parameters.Filename;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleMzCalibrationRouteApiCalibrationMzCalibrationGet {
        namespace Parameters {
            /**
             * Instrument
             */
            export type Instrument = /* Instrument */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            instrument?: /* Instrument */ Parameters.Instrument;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSampleRouteApiSamplesSampleItemIdGet {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetSamplesRouteApiSamplesGet {
        namespace Parameters {
            /**
             * Datetime Max
             */
            export type DatetimeMax = /* Datetime Max */ string /* date-time */ | null;
            /**
             * Datetime Min
             */
            export type DatetimeMin = /* Datetime Min */ string /* date-time */ | null;
            /**
             * Filename
             */
            export type Filename = /* Filename */ string | null;
            /**
             * Instrument
             */
            export type Instrument = /* Instrument */ string | null;
            /**
             * Limit
             */
            export type Limit = /* Limit */ number | null;
            /**
             * Match Category Min
             */
            export type MatchCategoryMin = /* Match Category Min */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = /* Page */ number | null;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sample File Id
             */
            export type SampleFileId = /* Sample File Id */ string | null;
            /**
             * Sample Item Id
             */
            export type SampleItemId = /* Sample Item Id */ string | null;
            /**
             * Sample Item Type
             */
            export type SampleItemType = /* Sample Item Type */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            sample_item_id?: /* Sample Item Id */ Parameters.SampleItemId;
            sample_file_id?: /* Sample File Id */ Parameters.SampleFileId;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            filename?: /* Filename */ Parameters.Filename;
            instrument?: /* Instrument */ Parameters.Instrument;
            sample_item_type?: /* Sample Item Type */ Parameters.SampleItemType;
            datetime_min?: /* Datetime Min */ Parameters.DatetimeMin;
            datetime_max?: /* Datetime Max */ Parameters.DatetimeMax;
            match_category_min?: /* Match Category Min */ Parameters.MatchCategoryMin;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCollectionRouteApiTargetCollectionsTargetCollectionIdGet {
        namespace Parameters {
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = string;
        }
        export interface PathParameters {
            target_collection_id: /* Target Collection Id */ Parameters.TargetCollectionId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCollectionsInSampleBatchRouteApiTargetAssociationsTargetCollectionsInSampleBatchGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
        }
        export interface QueryParameters {
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCollectionsRouteApiTargetCollectionsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Name
             */
            export type TargetCollectionName = /* Target Collection Name */ string | null;
            /**
             * Target Collection Type
             */
            export type TargetCollectionType = /* Target Collection Type */ string | null;
        }
        export interface QueryParameters {
            target_collection_type?: /* Target Collection Type */ Parameters.TargetCollectionType;
            target_collection_name?: /* Target Collection Name */ Parameters.TargetCollectionName;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCompoundInTargetCollectionsRouteApiTargetAssociationsTargetCompoundInTargetCollectionsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = /* Target Compound Id */ string | null;
        }
        export interface QueryParameters {
            target_compound_id?: /* Target Compound Id */ Parameters.TargetCompoundId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCompoundRouteApiTargetCompoundsTargetCompoundIdGet {
        namespace Parameters {
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = string;
        }
        export interface PathParameters {
            target_compound_id: /* Target Compound Id */ Parameters.TargetCompoundId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetCompoundsRouteApiTargetCompoundsGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Show Target Collection
             */
            export type ShowTargetCollection = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Compound Formula
             */
            export type TargetCompoundFormula = /* Target Compound Formula */ string | null;
            /**
             * Target Compound Name
             */
            export type TargetCompoundName = /* Target Compound Name */ string | null;
        }
        export interface QueryParameters {
            target_compound_name?: /* Target Compound Name */ Parameters.TargetCompoundName;
            target_compound_formula?: /* Target Compound Formula */ Parameters.TargetCompoundFormula;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            show_target_collection?: /* Show Target Collection */ Parameters.ShowTargetCollection;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetIonRouteApiTargetIonsTargetIonIdGet {
        namespace Parameters {
            /**
             * Target Ion Id
             */
            export type TargetIonId = string;
        }
        export interface PathParameters {
            target_ion_id: /* Target Ion Id */ Parameters.TargetIonId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetIonsRouteApiTargetIonsGet {
        namespace Parameters {
            /**
             * Ionization Mechanism Id
             */
            export type IonizationMechanismId = /* Ionization Mechanism Id */ string | null;
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Show Ionization Mechanism
             */
            export type ShowIonizationMechanism = boolean;
            /**
             * Show Target Collection
             */
            export type ShowTargetCollection = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Compound Id
             */
            export type TargetCompoundId = /* Target Compound Id */ string | null;
            /**
             * Target Ion Formula
             */
            export type TargetIonFormula = /* Target Ion Formula */ string | null;
        }
        export interface QueryParameters {
            target_compound_id?: /* Target Compound Id */ Parameters.TargetCompoundId;
            ionization_mechanism_id?: /* Ionization Mechanism Id */ Parameters.IonizationMechanismId;
            target_ion_formula?: /* Target Ion Formula */ Parameters.TargetIonFormula;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            show_target_collection?: /* Show Target Collection */ Parameters.ShowTargetCollection;
            show_ionization_mechanism?: /* Show Ionization Mechanism */ Parameters.ShowIonizationMechanism;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetIsotopeRouteApiTargetIsotopesTargetIsotopeIdGet {
        namespace Parameters {
            /**
             * Target Isotope Id
             */
            export type TargetIsotopeId = string;
        }
        export interface PathParameters {
            target_isotope_id: /* Target Isotope Id */ Parameters.TargetIsotopeId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetTargetIsotopesRouteApiTargetIsotopesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Max Mz
             */
            export type MaxMz = /* Max Mz */ number | null;
            /**
             * Max Relative Abundance
             */
            export type MaxRelativeAbundance = /* Max Relative Abundance */ number | null;
            /**
             * Min Mz
             */
            export type MinMz = /* Min Mz */ number | null;
            /**
             * Min Relative Abundance
             */
            export type MinRelativeAbundance = /* Min Relative Abundance */ number | null;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = /* Sample Batch Id */ string | null;
            /**
             * Show Filter Params
             */
            export type ShowFilterParams = boolean;
            /**
             * Show Target Collection
             */
            export type ShowTargetCollection = boolean;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = /* Target Collection Id */ string | null;
            /**
             * Target Ion Id
             */
            export type TargetIonId = /* Target Ion Id */ string | null;
        }
        export interface QueryParameters {
            target_ion_id?: /* Target Ion Id */ Parameters.TargetIonId;
            min_mz?: /* Min Mz */ Parameters.MinMz;
            max_mz?: /* Max Mz */ Parameters.MaxMz;
            min_relative_abundance?: /* Min Relative Abundance */ Parameters.MinRelativeAbundance;
            max_relative_abundance?: /* Max Relative Abundance */ Parameters.MaxRelativeAbundance;
            sample_batch_id?: /* Sample Batch Id */ Parameters.SampleBatchId;
            target_collection_id?: /* Target Collection Id */ Parameters.TargetCollectionId;
            show_target_collection?: /* Show Target Collection */ Parameters.ShowTargetCollection;
            show_filter_params?: /* Show Filter Params */ Parameters.ShowFilterParams;
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        export type RequestBody = /* Body_get_target_isotopes_route_api_target_isotopes_get */ Components.Schemas.BodyGetTargetIsotopesRouteApiTargetIsotopesGet;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetWorkspaceAdminRouteApiWorkspacesWorkspaceIdAdminGet {
        namespace Parameters {
            /**
             * Workspace Id
             */
            export type WorkspaceId = string;
        }
        export interface PathParameters {
            workspace_id: /* Workspace Id */ Parameters.WorkspaceId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetWorkspaceProtectedRouteApiWorkspacesWorkspaceIdProtectedGet {
        namespace Parameters {
            /**
             * Workspace Id
             */
            export type WorkspaceId = string;
        }
        export interface PathParameters {
            workspace_id: /* Workspace Id */ Parameters.WorkspaceId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetWorkspaceRouteApiWorkspacesWorkspaceIdGet {
        namespace Parameters {
            /**
             * Workspace Id
             */
            export type WorkspaceId = string;
        }
        export interface PathParameters {
            workspace_id: /* Workspace Id */ Parameters.WorkspaceId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace GetWorkspacesRouteApiWorkspacesGet {
        namespace Parameters {
            /**
             * Limit
             */
            export type Limit = number;
            /**
             * Order
             */
            export type Order = /* Order */ string | null;
            /**
             * Page
             */
            export type Page = number;
            /**
             * Sort
             */
            export type Sort = /* Sort */ string | null;
        }
        export interface QueryParameters {
            sort?: /* Sort */ Parameters.Sort;
            order?: /* Order */ Parameters.Order;
            page?: /* Page */ Parameters.Page;
            limit?: /* Limit */ Parameters.Limit;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* SampleBatchImportSamplesBody */ Components.Schemas.SampleBatchImportSamplesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* MatchComputeBody */ Components.Schemas.MatchComputeBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* MatchComputeBody */ Components.Schemas.MatchComputeBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace MatchRemoveAllRouteApiMatchRemoveAllDelete {
        namespace Responses {
            export type $200 = any;
        }
    }
    namespace MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* MatchRemovePayload */ Components.Schemas.MatchRemovePayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* MatchRemovePayload */ Components.Schemas.MatchRemovePayload;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace ProcessSampleItemRouteApiSampleItemsProcessPost {
        export type RequestBody = /* SampleItemProcessBody */ Components.Schemas.SampleItemProcessBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace RegisterRegisterApiAuthRegisterPost {
        export type RequestBody = /**
         * UserCreate
         * Schema for creating a new user. Provides fields required for user registration.
         */
        Components.Schemas.UserCreate;
        namespace Responses {
            export type $201 = /**
             * UserRead
             * Schema to read user data, typically used in responses to provide user details.
             */
            Components.Schemas.UserRead;
            export type $400 = /* ErrorModel */ Components.Schemas.ErrorModel;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* RematchBatchBody */ Components.Schemas.RematchBatchBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace RematchBatchesRouteApiMatchRematchBatchesPost {
        export type RequestBody = /* RematchBatchesBody */ Components.Schemas.RematchBatchesBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace RematchSampleRouteApiMatchRematchSampleSampleItemIdPost {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* RematchBody */ Components.Schemas.RematchBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace SampleBatchExportPeaksRouteApiSampleBatchesSampleBatchIdExportPeaksGet {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace SampleFileUploadRouteApiSampleFilesUploadPost {
        export type RequestBody = /* Body_sample_file_upload_route_api_sample_files_upload_post */ Components.Schemas.BodySampleFileUploadRouteApiSampleFilesUploadPost;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch {
        namespace Parameters {
            /**
             * Attribute Template Id
             */
            export type AttributeTemplateId = string;
        }
        export interface PathParameters {
            attribute_template_id: /* Attribute Template Id */ Parameters.AttributeTemplateId;
        }
        export type RequestBody = /* AttributeTemplateUpdateBody */ Components.Schemas.AttributeTemplateUpdateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch {
        namespace Parameters {
            /**
             * Sample Batch Id
             */
            export type SampleBatchId = string;
        }
        export interface PathParameters {
            sample_batch_id: /* Sample Batch Id */ Parameters.SampleBatchId;
        }
        export type RequestBody = /* SampleBatchUpdateBody */ Components.Schemas.SampleBatchUpdateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch {
        namespace Parameters {
            /**
             * Sample File Id
             */
            export type SampleFileId = string;
        }
        export interface PathParameters {
            sample_file_id: /* Sample File Id */ Parameters.SampleFileId;
        }
        export type RequestBody = /* SampleFileUpdate */ Components.Schemas.SampleFileUpdate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch {
        namespace Parameters {
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
        }
        export interface PathParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
        }
        export type RequestBody = /* SampleItemUpdate */ Components.Schemas.SampleItemUpdate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch {
        namespace Parameters {
            /**
             * Target Collection Id
             */
            export type TargetCollectionId = string;
        }
        export interface PathParameters {
            target_collection_id: /* Target Collection Id */ Parameters.TargetCollectionId;
        }
        export type RequestBody = /* TargetCollectionUpdateBody */ Components.Schemas.TargetCollectionUpdateBody;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateTargetCompoundRouteApiTargetCompoundsPatch {
        /**
         * Target Compounds
         */
        export type RequestBody = /* TargetCompoundUpdate */ Components.Schemas.TargetCompoundUpdate[];
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch {
        namespace Parameters {
            /**
             * Target Ion Id
             */
            export type TargetIonId = string;
        }
        export interface PathParameters {
            target_ion_id: /* Target Ion Id */ Parameters.TargetIonId;
        }
        export type RequestBody = /* TargetIonUpdate */ Components.Schemas.TargetIonUpdate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch {
        namespace Parameters {
            /**
             * Workspace Id
             */
            export type WorkspaceId = string;
        }
        export interface PathParameters {
            workspace_id: /* Workspace Id */ Parameters.WorkspaceId;
        }
        export type RequestBody = /* WorkspaceUpdate */ Components.Schemas.WorkspaceUpdate;
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UsersCurrentUserApiUsersMeGet {
        namespace Responses {
            export type $200 = /**
             * UserRead
             * Schema to read user data, typically used in responses to provide user details.
             */
            Components.Schemas.UserRead;
            export interface $401 {
            }
        }
    }
    namespace UsersDeleteUserApiUsersIdDelete {
        namespace Parameters {
            /**
             * Id
             */
            export type Id = string;
        }
        export interface PathParameters {
            id: /* Id */ Parameters.Id;
        }
        namespace Responses {
            export interface $204 {
            }
            export interface $401 {
            }
            export interface $403 {
            }
            export interface $404 {
            }
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UsersPatchCurrentUserApiUsersMePatch {
        export type RequestBody = /**
         * UserUpdate
         * Schema for updating existing user information. Fields can be partially updated.
         */
        Components.Schemas.UserUpdate;
        namespace Responses {
            export type $200 = /**
             * UserRead
             * Schema to read user data, typically used in responses to provide user details.
             */
            Components.Schemas.UserRead;
            export type $400 = /* ErrorModel */ Components.Schemas.ErrorModel;
            export interface $401 {
            }
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UsersPatchUserApiUsersIdPatch {
        namespace Parameters {
            /**
             * Id
             */
            export type Id = string;
        }
        export interface PathParameters {
            id: /* Id */ Parameters.Id;
        }
        export type RequestBody = /**
         * UserUpdate
         * Schema for updating existing user information. Fields can be partially updated.
         */
        Components.Schemas.UserUpdate;
        namespace Responses {
            export type $200 = /**
             * UserRead
             * Schema to read user data, typically used in responses to provide user details.
             */
            Components.Schemas.UserRead;
            export type $400 = /* ErrorModel */ Components.Schemas.ErrorModel;
            export interface $401 {
            }
            export interface $403 {
            }
            export interface $404 {
            }
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace UsersUserApiUsersIdGet {
        namespace Parameters {
            /**
             * Id
             */
            export type Id = string;
        }
        export interface PathParameters {
            id: /* Id */ Parameters.Id;
        }
        namespace Responses {
            export type $200 = /**
             * UserRead
             * Schema to read user data, typically used in responses to provide user details.
             */
            Components.Schemas.UserRead;
            export interface $401 {
            }
            export interface $403 {
            }
            export interface $404 {
            }
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
    namespace VisualizationIonFocusRouteApiVisualizationIonFocusGet {
        namespace Parameters {
            /**
             * Min Isotope Abundance
             */
            export type MinIsotopeAbundance = number;
            /**
             * Mz Tolerance
             */
            export type MzTolerance = number;
            /**
             * Peak Min Intensity
             */
            export type PeakMinIntensity = number;
            /**
             * Sample Item Id
             */
            export type SampleItemId = string;
            /**
             * Target Ion Id
             */
            export type TargetIonId = string;
        }
        export interface QueryParameters {
            sample_item_id: /* Sample Item Id */ Parameters.SampleItemId;
            target_ion_id: /* Target Ion Id */ Parameters.TargetIonId;
            min_isotope_abundance: /* Min Isotope Abundance */ Parameters.MinIsotopeAbundance;
            peak_min_intensity: /* Peak Min Intensity */ Parameters.PeakMinIntensity;
            mz_tolerance: /* Mz Tolerance */ Parameters.MzTolerance;
        }
        namespace Responses {
            export type $200 = any;
            export type $422 = /* HTTPValidationError */ Components.Schemas.HTTPValidationError;
        }
    }
}

export interface OperationMethods {
  /**
   * auth_jwt_login_api_auth_login_post - Auth:Jwt.Login
   */
  'auth_jwt_login_api_auth_login_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.AuthJwtLoginApiAuthLoginPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AuthJwtLoginApiAuthLoginPost.Responses.$200 | Paths.AuthJwtLoginApiAuthLoginPost.Responses.$204>
  /**
   * auth_jwt_logout_api_auth_logout_post - Auth:Jwt.Logout
   */
  'auth_jwt_logout_api_auth_logout_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AuthJwtLogoutApiAuthLogoutPost.Responses.$200 | Paths.AuthJwtLogoutApiAuthLogoutPost.Responses.$204>
  /**
   * register_register_api_auth_register_post - Register:Register
   */
  'register_register_api_auth_register_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.RegisterRegisterApiAuthRegisterPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.RegisterRegisterApiAuthRegisterPost.Responses.$201>
  /**
   * users_current_user_api_users_me_get - Users:Current User
   */
  'users_current_user_api_users_me_get'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UsersCurrentUserApiUsersMeGet.Responses.$200>
  /**
   * users_patch_current_user_api_users_me_patch - Users:Patch Current User
   */
  'users_patch_current_user_api_users_me_patch'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.UsersPatchCurrentUserApiUsersMePatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UsersPatchCurrentUserApiUsersMePatch.Responses.$200>
  /**
   * users_user_api_users__id__get - Users:User
   */
  'users_user_api_users__id__get'(
    parameters?: Parameters<Paths.UsersUserApiUsersIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UsersUserApiUsersIdGet.Responses.$200>
  /**
   * users_patch_user_api_users__id__patch - Users:Patch User
   */
  'users_patch_user_api_users__id__patch'(
    parameters?: Parameters<Paths.UsersPatchUserApiUsersIdPatch.PathParameters> | null,
    data?: Paths.UsersPatchUserApiUsersIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UsersPatchUserApiUsersIdPatch.Responses.$200>
  /**
   * users_delete_user_api_users__id__delete - Users:Delete User
   */
  'users_delete_user_api_users__id__delete'(
    parameters?: Parameters<Paths.UsersDeleteUserApiUsersIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UsersDeleteUserApiUsersIdDelete.Responses.$204>
  /**
   * get_workspaces_route_api_workspaces_get - Get Workspaces Route
   */
  'get_workspaces_route_api_workspaces_get'(
    parameters?: Parameters<Paths.GetWorkspacesRouteApiWorkspacesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetWorkspacesRouteApiWorkspacesGet.Responses.$200>
  /**
   * create_workspace_route_api_workspaces_post - Create Workspace Route
   */
  'create_workspace_route_api_workspaces_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateWorkspaceRouteApiWorkspacesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateWorkspaceRouteApiWorkspacesPost.Responses.$200>
  /**
   * get_workspace_route_api_workspaces__workspace_id__get - Get Workspace Route
   */
  'get_workspace_route_api_workspaces__workspace_id__get'(
    parameters?: Parameters<Paths.GetWorkspaceRouteApiWorkspacesWorkspaceIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetWorkspaceRouteApiWorkspacesWorkspaceIdGet.Responses.$200>
  /**
   * update_workspace_route_api_workspaces__workspace_id__patch - Update Workspace Route
   */
  'update_workspace_route_api_workspaces__workspace_id__patch'(
    parameters?: Parameters<Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.PathParameters> | null,
    data?: Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.Responses.$200>
  /**
   * delete_workspace_route_api_workspaces__workspace_id__delete - Delete Workspace Route
   */
  'delete_workspace_route_api_workspaces__workspace_id__delete'(
    parameters?: Parameters<Paths.DeleteWorkspaceRouteApiWorkspacesWorkspaceIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteWorkspaceRouteApiWorkspacesWorkspaceIdDelete.Responses.$200>
  /**
   * get_workspace_protected_route_api_workspaces__workspace_id__protected_get - Get Workspace Protected Route
   */
  'get_workspace_protected_route_api_workspaces__workspace_id__protected_get'(
    parameters?: Parameters<Paths.GetWorkspaceProtectedRouteApiWorkspacesWorkspaceIdProtectedGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetWorkspaceProtectedRouteApiWorkspacesWorkspaceIdProtectedGet.Responses.$200>
  /**
   * get_workspace_admin_route_api_workspaces__workspace_id__admin_get - Get Workspace Admin Route
   */
  'get_workspace_admin_route_api_workspaces__workspace_id__admin_get'(
    parameters?: Parameters<Paths.GetWorkspaceAdminRouteApiWorkspacesWorkspaceIdAdminGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetWorkspaceAdminRouteApiWorkspacesWorkspaceIdAdminGet.Responses.$200>
  /**
   * get_sample_batches_route_api_sample_batches_get - Get Sample Batches Route
   */
  'get_sample_batches_route_api_sample_batches_get'(
    parameters?: Parameters<Paths.GetSampleBatchesRouteApiSampleBatchesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleBatchesRouteApiSampleBatchesGet.Responses.$200>
  /**
   * create_sample_batch_route_api_sample_batches_post - Create Sample Batch Route
   */
  'create_sample_batch_route_api_sample_batches_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateSampleBatchRouteApiSampleBatchesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateSampleBatchRouteApiSampleBatchesPost.Responses.$200>
  /**
   * get_sample_batch_route_api_sample_batches__sample_batch_id__get - Get Sample Batch Route
   */
  'get_sample_batch_route_api_sample_batches__sample_batch_id__get'(
    parameters?: Parameters<Paths.GetSampleBatchRouteApiSampleBatchesSampleBatchIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleBatchRouteApiSampleBatchesSampleBatchIdGet.Responses.$200>
  /**
   * update_sample_batch_route_api_sample_batches__sample_batch_id__patch - Update Sample Batch Route
   */
  'update_sample_batch_route_api_sample_batches__sample_batch_id__patch'(
    parameters?: Parameters<Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.PathParameters> | null,
    data?: Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.Responses.$200>
  /**
   * delete_sample_batch_route_api_sample_batches__sample_batch_id__delete - Delete Sample Batch Route
   */
  'delete_sample_batch_route_api_sample_batches__sample_batch_id__delete'(
    parameters?: Parameters<Paths.DeleteSampleBatchRouteApiSampleBatchesSampleBatchIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteSampleBatchRouteApiSampleBatchesSampleBatchIdDelete.Responses.$200>
  /**
   * get_batch_targets_route_api_sample_batches__sample_batch_id__targets_get - Get Batch Targets Route
   */
  'get_batch_targets_route_api_sample_batches__sample_batch_id__targets_get'(
    parameters?: Parameters<Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.QueryParameters & Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.Responses.$200>
  /**
   * import_sample_items_route_api_sample_batches__sample_batch_id__import_post - Import Sample Items Route
   */
  'import_sample_items_route_api_sample_batches__sample_batch_id__import_post'(
    parameters?: Parameters<Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.PathParameters> | null,
    data?: Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.Responses.$200>
  /**
   * copy_sample_batch_route_api_sample_batches__sample_batch_id__copy_post - Copy Sample Batch Route
   */
  'copy_sample_batch_route_api_sample_batches__sample_batch_id__copy_post'(
    parameters?: Parameters<Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.PathParameters> | null,
    data?: Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.Responses.$200>
  /**
   * sample_batch_export_peaks_route_api_sample_batches__sample_batch_id__export_peaks_get - Sample Batch Export Peaks Route
   */
  'sample_batch_export_peaks_route_api_sample_batches__sample_batch_id__export_peaks_get'(
    parameters?: Parameters<Paths.SampleBatchExportPeaksRouteApiSampleBatchesSampleBatchIdExportPeaksGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.SampleBatchExportPeaksRouteApiSampleBatchesSampleBatchIdExportPeaksGet.Responses.$200>
  /**
   * get_samples_route_api_samples_get - Get Samples Route
   */
  'get_samples_route_api_samples_get'(
    parameters?: Parameters<Paths.GetSamplesRouteApiSamplesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSamplesRouteApiSamplesGet.Responses.$200>
  /**
   * get_sample_route_api_samples__sample_item_id__get - Get Sample Route
   */
  'get_sample_route_api_samples__sample_item_id__get'(
    parameters?: Parameters<Paths.GetSampleRouteApiSamplesSampleItemIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleRouteApiSamplesSampleItemIdGet.Responses.$200>
  /**
   * get_sample_items_route_api_sample_items_get - Get Sample Items Route
   */
  'get_sample_items_route_api_sample_items_get'(
    parameters?: Parameters<Paths.GetSampleItemsRouteApiSampleItemsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleItemsRouteApiSampleItemsGet.Responses.$200>
  /**
   * create_sample_item_route_api_sample_items_post - Create Sample Item Route
   */
  'create_sample_item_route_api_sample_items_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateSampleItemRouteApiSampleItemsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateSampleItemRouteApiSampleItemsPost.Responses.$200>
  /**
   * get_sample_item_route_api_sample_items__sample_item_id__get - Get Sample Item Route
   */
  'get_sample_item_route_api_sample_items__sample_item_id__get'(
    parameters?: Parameters<Paths.GetSampleItemRouteApiSampleItemsSampleItemIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleItemRouteApiSampleItemsSampleItemIdGet.Responses.$200>
  /**
   * update_sample_item_route_api_sample_items__sample_item_id__patch - Update Sample Item Route
   */
  'update_sample_item_route_api_sample_items__sample_item_id__patch'(
    parameters?: Parameters<Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.PathParameters> | null,
    data?: Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.Responses.$200>
  /**
   * delete_sample_item_route_api_sample_items__sample_item_id__delete - Delete Sample Item Route
   */
  'delete_sample_item_route_api_sample_items__sample_item_id__delete'(
    parameters?: Parameters<Paths.DeleteSampleItemRouteApiSampleItemsSampleItemIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteSampleItemRouteApiSampleItemsSampleItemIdDelete.Responses.$200>
  /**
   * copy_sample_item_route_api_sample_items__sample_item_id__copy_post - Copy Sample Item Route
   */
  'copy_sample_item_route_api_sample_items__sample_item_id__copy_post'(
    parameters?: Parameters<Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.PathParameters> | null,
    data?: Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.Responses.$200>
  /**
   * process_sample_item_route_api_sample_items_process_post - Process Sample Item Route
   */
  'process_sample_item_route_api_sample_items_process_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.ProcessSampleItemRouteApiSampleItemsProcessPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.ProcessSampleItemRouteApiSampleItemsProcessPost.Responses.$200>
  /**
   * get_sample_files_route_api_sample_files_get - Get Sample Files Route
   */
  'get_sample_files_route_api_sample_files_get'(
    parameters?: Parameters<Paths.GetSampleFilesRouteApiSampleFilesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleFilesRouteApiSampleFilesGet.Responses.$200>
  /**
   * create_sample_file_route_api_sample_files_post - Create Sample File Route
   */
  'create_sample_file_route_api_sample_files_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateSampleFileRouteApiSampleFilesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateSampleFileRouteApiSampleFilesPost.Responses.$200>
  /**
   * get_recent_sample_files_route_api_sample_files_recent_get - Get Recent Sample Files Route
   */
  'get_recent_sample_files_route_api_sample_files_recent_get'(
    parameters?: Parameters<Paths.GetRecentSampleFilesRouteApiSampleFilesRecentGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetRecentSampleFilesRouteApiSampleFilesRecentGet.Responses.$200>
  /**
   * get_sample_file_route_api_sample_files__sample_file_id__get - Get Sample File Route
   */
  'get_sample_file_route_api_sample_files__sample_file_id__get'(
    parameters?: Parameters<Paths.GetSampleFileRouteApiSampleFilesSampleFileIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleFileRouteApiSampleFilesSampleFileIdGet.Responses.$200>
  /**
   * update_sample_file_route_api_sample_files__sample_file_id__patch - Update Sample File Route
   */
  'update_sample_file_route_api_sample_files__sample_file_id__patch'(
    parameters?: Parameters<Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.PathParameters> | null,
    data?: Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.Responses.$200>
  /**
   * delete_sample_file_route_api_sample_files__sample_file_id__delete - Delete Sample File Route
   */
  'delete_sample_file_route_api_sample_files__sample_file_id__delete'(
    parameters?: Parameters<Paths.DeleteSampleFileRouteApiSampleFilesSampleFileIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteSampleFileRouteApiSampleFilesSampleFileIdDelete.Responses.$200>
  /**
   * get_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_get - Get Sample File Peaks Route
   */
  'get_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_get'(
    parameters?: Parameters<Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.QueryParameters & Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.Responses.$200>
  /**
   * compute_all_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_compute_get - Compute All Sample File Peaks Route
   */
  'compute_all_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_compute_get'(
    parameters?: Parameters<Paths.ComputeAllSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksComputeGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.ComputeAllSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksComputeGet.Responses.$200>
  /**
   * get_sample_file_peak_timeseries_route_api_sample_files__sample_file_id__peaks_timeseries_post - Get Sample File Peak Timeseries Route
   */
  'get_sample_file_peak_timeseries_route_api_sample_files__sample_file_id__peaks_timeseries_post'(
    parameters?: Parameters<Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.PathParameters> | null,
    data?: Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.Responses.$200>
  /**
   * get_sample_file_spectrum_route_api_sample_files__sample_file_id__spectrum_get - Get Sample File Spectrum Route
   */
  'get_sample_file_spectrum_route_api_sample_files__sample_file_id__spectrum_get'(
    parameters?: Parameters<Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.QueryParameters & Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.Responses.$200>
  /**
   * sample_file_upload_route_api_sample_files_upload_post - Sample File Upload Route
   * 
   * Uploads a sample file to the server.
   * 
   * This route takes an uploaded file from a form field and saves it in the `filestreams` directory
   * on the server. It validates the file's size and extension before uploading.
   * 
   * :param file: The file to be uploaded, provided in a form field.
   * :type file: UploadFile
   * :return: A JSON response indicating the success or failure of the upload.
   * :rtype: JSONResponse
   */
  'sample_file_upload_route_api_sample_files_upload_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.SampleFileUploadRouteApiSampleFilesUploadPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.SampleFileUploadRouteApiSampleFilesUploadPost.Responses.$200>
  /**
   * get_sample_mz_calibration_route_api_calibration_mz_calibration_get - Get Sample Mz Calibration Route
   */
  'get_sample_mz_calibration_route_api_calibration_mz_calibration_get'(
    parameters?: Parameters<Paths.GetSampleMzCalibrationRouteApiCalibrationMzCalibrationGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleMzCalibrationRouteApiCalibrationMzCalibrationGet.Responses.$200>
  /**
   * calibration_mz_fit_route_api_calibration_mz_fit_post - Calibration Mz Fit Route
   */
  'calibration_mz_fit_route_api_calibration_mz_fit_post'(
    parameters?: Parameters<Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.QueryParameters> | null,
    data?: Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.Responses.$200>
  /**
   * calibration_mz_apply_route_api_calibration_mz_apply_post - Calibration Mz Apply Route
   */
  'calibration_mz_apply_route_api_calibration_mz_apply_post'(
    parameters?: Parameters<Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.QueryParameters> | null,
    data?: Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.Responses.$200>
  /**
   * calibration_mz_calibrate_sample_route_api_calibration_mz_calibrate_sample__sample_item_id__post - Calibration Mz Calibrate Sample Route
   */
  'calibration_mz_calibrate_sample_route_api_calibration_mz_calibrate_sample__sample_item_id__post'(
    parameters?: Parameters<Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.PathParameters> | null,
    data?: Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.Responses.$200>
  /**
   * calibration_mz_calibrate_batch_route_api_calibration_mz_calibrate_batch__sample_batch_id__post - Calibration Mz Calibrate Batch Route
   */
  'calibration_mz_calibrate_batch_route_api_calibration_mz_calibrate_batch__sample_batch_id__post'(
    parameters?: Parameters<Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.PathParameters> | null,
    data?: Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.Responses.$200>
  /**
   * get_target_collections_route_api_target_collections_get - Get Target Collections Route
   */
  'get_target_collections_route_api_target_collections_get'(
    parameters?: Parameters<Paths.GetTargetCollectionsRouteApiTargetCollectionsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCollectionsRouteApiTargetCollectionsGet.Responses.$200>
  /**
   * create_target_collection_route_api_target_collections_post - Create Target Collection Route
   */
  'create_target_collection_route_api_target_collections_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateTargetCollectionRouteApiTargetCollectionsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateTargetCollectionRouteApiTargetCollectionsPost.Responses.$200>
  /**
   * get_target_collection_route_api_target_collections__target_collection_id__get - Get Target Collection Route
   */
  'get_target_collection_route_api_target_collections__target_collection_id__get'(
    parameters?: Parameters<Paths.GetTargetCollectionRouteApiTargetCollectionsTargetCollectionIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCollectionRouteApiTargetCollectionsTargetCollectionIdGet.Responses.$200>
  /**
   * update_target_collection_route_api_target_collections__target_collection_id__patch - Update Target Collection Route
   */
  'update_target_collection_route_api_target_collections__target_collection_id__patch'(
    parameters?: Parameters<Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.PathParameters> | null,
    data?: Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.Responses.$200>
  /**
   * delete_target_collection_route_api_target_collections__target_collection_id__delete - Delete Target Collection Route
   */
  'delete_target_collection_route_api_target_collections__target_collection_id__delete'(
    parameters?: Parameters<Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.QueryParameters & Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.Responses.$200>
  /**
   * get_target_collections_in_sample_batch_route_api_target_associations_target_collections_in_sample_batch_get - Get Target Collections In Sample Batch Route
   */
  'get_target_collections_in_sample_batch_route_api_target_associations_target_collections_in_sample_batch_get'(
    parameters?: Parameters<Paths.GetTargetCollectionsInSampleBatchRouteApiTargetAssociationsTargetCollectionsInSampleBatchGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCollectionsInSampleBatchRouteApiTargetAssociationsTargetCollectionsInSampleBatchGet.Responses.$200>
  /**
   * get_target_compounds_route_api_target_compounds_get - Get Target Compounds Route
   */
  'get_target_compounds_route_api_target_compounds_get'(
    parameters?: Parameters<Paths.GetTargetCompoundsRouteApiTargetCompoundsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCompoundsRouteApiTargetCompoundsGet.Responses.$200>
  /**
   * create_target_compounds_route_api_target_compounds_post - Create Target Compounds Route
   */
  'create_target_compounds_route_api_target_compounds_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateTargetCompoundsRouteApiTargetCompoundsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateTargetCompoundsRouteApiTargetCompoundsPost.Responses.$200>
  /**
   * update_target_compound_route_api_target_compounds_patch - Update Target Compound Route
   */
  'update_target_compound_route_api_target_compounds_patch'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.UpdateTargetCompoundRouteApiTargetCompoundsPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateTargetCompoundRouteApiTargetCompoundsPatch.Responses.$200>
  /**
   * get_target_compound_route_api_target_compounds__target_compound_id__get - Get Target Compound Route
   */
  'get_target_compound_route_api_target_compounds__target_compound_id__get'(
    parameters?: Parameters<Paths.GetTargetCompoundRouteApiTargetCompoundsTargetCompoundIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCompoundRouteApiTargetCompoundsTargetCompoundIdGet.Responses.$200>
  /**
   * delete_target_compound_route_api_target_compounds__target_compound_id__delete - Delete Target Compound Route
   */
  'delete_target_compound_route_api_target_compounds__target_compound_id__delete'(
    parameters?: Parameters<Paths.DeleteTargetCompoundRouteApiTargetCompoundsTargetCompoundIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteTargetCompoundRouteApiTargetCompoundsTargetCompoundIdDelete.Responses.$200>
  /**
   * get_target_compound_in_target_collections_route_api_target_associations_target_compound_in_target_collections_get - Get Target Compound In Target Collections Route
   */
  'get_target_compound_in_target_collections_route_api_target_associations_target_compound_in_target_collections_get'(
    parameters?: Parameters<Paths.GetTargetCompoundInTargetCollectionsRouteApiTargetAssociationsTargetCompoundInTargetCollectionsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetCompoundInTargetCollectionsRouteApiTargetAssociationsTargetCompoundInTargetCollectionsGet.Responses.$200>
  /**
   * get_target_ions_route_api_target_ions_get - Get Target Ions Route
   */
  'get_target_ions_route_api_target_ions_get'(
    parameters?: Parameters<Paths.GetTargetIonsRouteApiTargetIonsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetIonsRouteApiTargetIonsGet.Responses.$200>
  /**
   * get_target_ion_route_api_target_ions__target_ion_id__get - Get Target Ion Route
   */
  'get_target_ion_route_api_target_ions__target_ion_id__get'(
    parameters?: Parameters<Paths.GetTargetIonRouteApiTargetIonsTargetIonIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetIonRouteApiTargetIonsTargetIonIdGet.Responses.$200>
  /**
   * update_target_ion_route_api_target_ions__target_ion_id__patch - Update Target Ion Route
   */
  'update_target_ion_route_api_target_ions__target_ion_id__patch'(
    parameters?: Parameters<Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.PathParameters> | null,
    data?: Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.Responses.$200>
  /**
   * get_ionization_mechanisms_route_api_ionization_mechanisms_get - Get Ionization Mechanisms Route
   */
  'get_ionization_mechanisms_route_api_ionization_mechanisms_get'(
    parameters?: Parameters<Paths.GetIonizationMechanismsRouteApiIonizationMechanismsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetIonizationMechanismsRouteApiIonizationMechanismsGet.Responses.$200>
  /**
   * create_ionization_mechanism_route_api_ionization_mechanisms_post - Create Ionization Mechanism Route
   */
  'create_ionization_mechanism_route_api_ionization_mechanisms_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateIonizationMechanismRouteApiIonizationMechanismsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateIonizationMechanismRouteApiIonizationMechanismsPost.Responses.$200>
  /**
   * get_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__get - Get Ionization Mechanism Route
   */
  'get_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__get'(
    parameters?: Parameters<Paths.GetIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdGet.Responses.$200>
  /**
   * delete_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__delete - Delete Ionization Mechanism Route
   */
  'delete_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__delete'(
    parameters?: Parameters<Paths.DeleteIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdDelete.Responses.$200>
  /**
   * get_target_isotopes_route_api_target_isotopes_get - Get Target Isotopes Route
   */
  'get_target_isotopes_route_api_target_isotopes_get'(
    parameters?: Parameters<Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.QueryParameters> | null,
    data?: Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.Responses.$200>
  /**
   * get_target_isotope_route_api_target_isotopes__target_isotope_id__get - Get Target Isotope Route
   */
  'get_target_isotope_route_api_target_isotopes__target_isotope_id__get'(
    parameters?: Parameters<Paths.GetTargetIsotopeRouteApiTargetIsotopesTargetIsotopeIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetTargetIsotopeRouteApiTargetIsotopesTargetIsotopeIdGet.Responses.$200>
  /**
   * rematch_batches_route_api_match_rematch_batches_post - Rematch Batches Route
   */
  'rematch_batches_route_api_match_rematch_batches_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.RematchBatchesRouteApiMatchRematchBatchesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.RematchBatchesRouteApiMatchRematchBatchesPost.Responses.$200>
  /**
   * rematch_batch_route_api_match_rematch_batch__sample_batch_id__post - Rematch Batch Route
   */
  'rematch_batch_route_api_match_rematch_batch__sample_batch_id__post'(
    parameters?: Parameters<Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.PathParameters> | null,
    data?: Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.Responses.$200>
  /**
   * match_compute_batch_route_api_match_compute_batch__sample_batch_id__post - Match Compute Batch Route
   */
  'match_compute_batch_route_api_match_compute_batch__sample_batch_id__post'(
    parameters?: Parameters<Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.PathParameters> | null,
    data?: Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.Responses.$200>
  /**
   * match_remove_batch_route_api_match_remove_batch__sample_batch_id__delete - Match Remove Batch Route
   */
  'match_remove_batch_route_api_match_remove_batch__sample_batch_id__delete'(
    parameters?: Parameters<Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.PathParameters> | null,
    data?: Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.Responses.$200>
  /**
   * rematch_sample_route_api_match_rematch_sample__sample_item_id__post - Rematch Sample Route
   */
  'rematch_sample_route_api_match_rematch_sample__sample_item_id__post'(
    parameters?: Parameters<Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.PathParameters> | null,
    data?: Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.Responses.$200>
  /**
   * match_remove_sample_route_api_match_remove_sample__sample_item_id__delete - Match Remove Sample Route
   */
  'match_remove_sample_route_api_match_remove_sample__sample_item_id__delete'(
    parameters?: Parameters<Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.PathParameters> | null,
    data?: Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.Responses.$200>
  /**
   * match_compute_sample_route_api_match_compute_sample__sample_item_id__post - Match Compute Sample Route
   */
  'match_compute_sample_route_api_match_compute_sample__sample_item_id__post'(
    parameters?: Parameters<Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.PathParameters> | null,
    data?: Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.Responses.$200>
  /**
   * match_remove_all_route_api_match_remove_all_delete - Match Remove All Route
   * 
   * Endpoint to delete all match data across the system.
   */
  'match_remove_all_route_api_match_remove_all_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.MatchRemoveAllRouteApiMatchRemoveAllDelete.Responses.$200>
  /**
   * aggregate_batch_match_isotope_filtered_data_route_api_match_aggregate_batch__sample_batch_id__isotope_post - Aggregate Batch Match Isotope Filtered Data Route
   */
  'aggregate_batch_match_isotope_filtered_data_route_api_match_aggregate_batch__sample_batch_id__isotope_post'(
    parameters?: Parameters<Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.PathParameters> | null,
    data?: Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.Responses.$200>
  /**
   * aggregate_batch_matches_route_api_match_aggregate_batch__sample_batch_id__post - Aggregate Batch Matches Route
   */
  'aggregate_batch_matches_route_api_match_aggregate_batch__sample_batch_id__post'(
    parameters?: Parameters<Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.PathParameters> | null,
    data?: Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.Responses.$200>
  /**
   * aggregate_and_create_batch_matches_route_api_match_aggregate_batch__sample_batch_id__save_post - Aggregate And Create Batch Matches Route
   */
  'aggregate_and_create_batch_matches_route_api_match_aggregate_batch__sample_batch_id__save_post'(
    parameters?: Parameters<Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.PathParameters> | null,
    data?: Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.Responses.$200>
  /**
   * aggregate_and_recreate_matches_route_api_match_aggregate_batch__sample_batch_id__resave_post - Aggregate And Recreate Matches Route
   */
  'aggregate_and_recreate_matches_route_api_match_aggregate_batch__sample_batch_id__resave_post'(
    parameters?: Parameters<Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.PathParameters> | null,
    data?: Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.Responses.$200>
  /**
   * get_batch_and_aggregated_matches_route_api_match_aggregate_batch__sample_batch_id__all_get - Get Batch And Aggregated Matches Route
   */
  'get_batch_and_aggregated_matches_route_api_match_aggregate_batch__sample_batch_id__all_get'(
    parameters?: Parameters<Paths.GetBatchAndAggregatedMatchesRouteApiMatchAggregateBatchSampleBatchIdAllGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetBatchAndAggregatedMatchesRouteApiMatchAggregateBatchSampleBatchIdAllGet.Responses.$200>
  /**
   * aggregate_sample_match_isotope_filtered_data_route_api_match_aggregate_sample__sample_item_id__isotope_post - Aggregate Sample Match Isotope Filtered Data Route
   */
  'aggregate_sample_match_isotope_filtered_data_route_api_match_aggregate_sample__sample_item_id__isotope_post'(
    parameters?: Parameters<Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.PathParameters> | null,
    data?: Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.Responses.$200>
  /**
   * aggregate_sample_match_ion_route_api_match_aggregate_sample__sample_item_id__ion_post - Aggregate Sample Match Ion Route
   */
  'aggregate_sample_match_ion_route_api_match_aggregate_sample__sample_item_id__ion_post'(
    parameters?: Parameters<Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.PathParameters> | null,
    data?: Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.Responses.$200>
  /**
   * aggregate_sample_match_compound_route_api_match_aggregate_sample__sample_item_id__compound_post - Aggregate Sample Match Compound Route
   */
  'aggregate_sample_match_compound_route_api_match_aggregate_sample__sample_item_id__compound_post'(
    parameters?: Parameters<Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.PathParameters> | null,
    data?: Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.Responses.$200>
  /**
   * aggregate_sample_matches_route_api_match_aggregate_sample__sample_item_id__post - Aggregate Sample Matches Route
   */
  'aggregate_sample_matches_route_api_match_aggregate_sample__sample_item_id__post'(
    parameters?: Parameters<Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.PathParameters> | null,
    data?: Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.Responses.$200>
  /**
   * aggregate_and_create_sample_matches_route_api_match_aggregate_sample__sample_item_id__save_post - Aggregate And Create Sample Matches Route
   */
  'aggregate_and_create_sample_matches_route_api_match_aggregate_sample__sample_item_id__save_post'(
    parameters?: Parameters<Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.PathParameters> | null,
    data?: Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.Responses.$200>
  /**
   * get_sample_aggregate_matches_route_api_match_aggregate_sample__sample_item_id__all_get - Get Sample Aggregate Matches Route
   */
  'get_sample_aggregate_matches_route_api_match_aggregate_sample__sample_item_id__all_get'(
    parameters?: Parameters<Paths.GetSampleAggregateMatchesRouteApiMatchAggregateSampleSampleItemIdAllGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetSampleAggregateMatchesRouteApiMatchAggregateSampleSampleItemIdAllGet.Responses.$200>
  /**
   * get_match_samples_route_api_match_samples_get - Get Match Samples Route
   */
  'get_match_samples_route_api_match_samples_get'(
    parameters?: Parameters<Paths.GetMatchSamplesRouteApiMatchSamplesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSamplesRouteApiMatchSamplesGet.Responses.$200>
  /**
   * create_match_samples_route_api_match_samples_post - Create Match Samples Route
   */
  'create_match_samples_route_api_match_samples_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchSamplesRouteApiMatchSamplesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchSamplesRouteApiMatchSamplesPost.Responses.$200>
  /**
   * delete_match_samples_route_api_match_samples_delete - Delete Match Samples Route
   */
  'delete_match_samples_route_api_match_samples_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchSamplesRouteApiMatchSamplesDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchSamplesRouteApiMatchSamplesDelete.Responses.$200>
  /**
   * get_match_sample_route_api_match_samples__match_sample_id__get - Get Match Sample Route
   */
  'get_match_sample_route_api_match_samples__match_sample_id__get'(
    parameters?: Parameters<Paths.GetMatchSampleRouteApiMatchSamplesMatchSampleIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSampleRouteApiMatchSamplesMatchSampleIdGet.Responses.$200>
  /**
   * get_match_collections_route_api_match_collections_get - Get Match Collections Route
   */
  'get_match_collections_route_api_match_collections_get'(
    parameters?: Parameters<Paths.GetMatchCollectionsRouteApiMatchCollectionsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchCollectionsRouteApiMatchCollectionsGet.Responses.$200>
  /**
   * create_match_collections_route_api_match_collections_post - Create Match Collections Route
   */
  'create_match_collections_route_api_match_collections_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchCollectionsRouteApiMatchCollectionsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchCollectionsRouteApiMatchCollectionsPost.Responses.$200>
  /**
   * delete_match_collections_route_api_match_collections_delete - Delete Match Collections Route
   */
  'delete_match_collections_route_api_match_collections_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchCollectionsRouteApiMatchCollectionsDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchCollectionsRouteApiMatchCollectionsDelete.Responses.$200>
  /**
   * get_match_collection_route_api_match_collections__match_collection_id__get - Get Match Collection Route
   */
  'get_match_collection_route_api_match_collections__match_collection_id__get'(
    parameters?: Parameters<Paths.GetMatchCollectionRouteApiMatchCollectionsMatchCollectionIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchCollectionRouteApiMatchCollectionsMatchCollectionIdGet.Responses.$200>
  /**
   * get_all_match_compounds_route_api_match_compounds_get - Get All Match Compounds Route
   */
  'get_all_match_compounds_route_api_match_compounds_get'(
    parameters?: Parameters<Paths.GetAllMatchCompoundsRouteApiMatchCompoundsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetAllMatchCompoundsRouteApiMatchCompoundsGet.Responses.$200>
  /**
   * create_match_compounds_route_api_match_compounds_post - Create Match Compounds Route
   */
  'create_match_compounds_route_api_match_compounds_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchCompoundsRouteApiMatchCompoundsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchCompoundsRouteApiMatchCompoundsPost.Responses.$200>
  /**
   * delete_match_compounds_route_api_match_compounds_delete - Delete Match Compounds Route
   */
  'delete_match_compounds_route_api_match_compounds_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchCompoundsRouteApiMatchCompoundsDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchCompoundsRouteApiMatchCompoundsDelete.Responses.$200>
  /**
   * get_match_compound_route_api_match_compounds__match_compound_id__get - Get Match Compound Route
   */
  'get_match_compound_route_api_match_compounds__match_compound_id__get'(
    parameters?: Parameters<Paths.GetMatchCompoundRouteApiMatchCompoundsMatchCompoundIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchCompoundRouteApiMatchCompoundsMatchCompoundIdGet.Responses.$200>
  /**
   * get_match_ions_route_api_match_ions_get - Get Match Ions Route
   */
  'get_match_ions_route_api_match_ions_get'(
    parameters?: Parameters<Paths.GetMatchIonsRouteApiMatchIonsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchIonsRouteApiMatchIonsGet.Responses.$200>
  /**
   * create_match_ions_route_api_match_ions_post - Create Match Ions Route
   */
  'create_match_ions_route_api_match_ions_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchIonsRouteApiMatchIonsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchIonsRouteApiMatchIonsPost.Responses.$200>
  /**
   * delete_match_ions_route_api_match_ions_delete - Delete Match Ions Route
   */
  'delete_match_ions_route_api_match_ions_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchIonsRouteApiMatchIonsDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchIonsRouteApiMatchIonsDelete.Responses.$200>
  /**
   * get_match_ion_route_api_match_ions__match_ion_id__get - Get Match Ion Route
   */
  'get_match_ion_route_api_match_ions__match_ion_id__get'(
    parameters?: Parameters<Paths.GetMatchIonRouteApiMatchIonsMatchIonIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchIonRouteApiMatchIonsMatchIonIdGet.Responses.$200>
  /**
   * get_match_ratings_route_api_match_ratings_get - Get Match Ratings Route
   */
  'get_match_ratings_route_api_match_ratings_get'(
    parameters?: Parameters<Paths.GetMatchRatingsRouteApiMatchRatingsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchRatingsRouteApiMatchRatingsGet.Responses.$200>
  /**
   * create_match_rating_route_api_match_ratings_post - Create Match Rating Route
   */
  'create_match_rating_route_api_match_ratings_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchRatingRouteApiMatchRatingsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchRatingRouteApiMatchRatingsPost.Responses.$200>
  /**
   * get_match_rating_route_api_match_ratings__match_rating_id__get - Get Match Rating Route
   */
  'get_match_rating_route_api_match_ratings__match_rating_id__get'(
    parameters?: Parameters<Paths.GetMatchRatingRouteApiMatchRatingsMatchRatingIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchRatingRouteApiMatchRatingsMatchRatingIdGet.Responses.$200>
  /**
   * get_match_interferences_route_api_match_interferences_get - Get Match Interferences Route
   */
  'get_match_interferences_route_api_match_interferences_get'(
    parameters?: Parameters<Paths.GetMatchInterferencesRouteApiMatchInterferencesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchInterferencesRouteApiMatchInterferencesGet.Responses.$200>
  /**
   * create_match_interferences_route_api_match_interferences_post - Create Match Interferences Route
   */
  'create_match_interferences_route_api_match_interferences_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchInterferencesRouteApiMatchInterferencesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchInterferencesRouteApiMatchInterferencesPost.Responses.$200>
  /**
   * delete_match_interferences_route_api_match_interferences_delete - Delete Match Interferences Route
   */
  'delete_match_interferences_route_api_match_interferences_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchInterferencesRouteApiMatchInterferencesDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchInterferencesRouteApiMatchInterferencesDelete.Responses.$200>
  /**
   * get_match_interference_route_api_match_interferences__match_interference_id__get - Get Match Interference Route
   */
  'get_match_interference_route_api_match_interferences__match_interference_id__get'(
    parameters?: Parameters<Paths.GetMatchInterferenceRouteApiMatchInterferencesMatchInterferenceIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchInterferenceRouteApiMatchInterferencesMatchInterferenceIdGet.Responses.$200>
  /**
   * get_match_isotopes_route_api_match_isotopes_get - Get Match Isotopes Route
   */
  'get_match_isotopes_route_api_match_isotopes_get'(
    parameters?: Parameters<Paths.GetMatchIsotopesRouteApiMatchIsotopesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchIsotopesRouteApiMatchIsotopesGet.Responses.$200>
  /**
   * create_match_isotopes_route_api_match_isotopes_post - Create Match Isotopes Route
   */
  'create_match_isotopes_route_api_match_isotopes_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateMatchIsotopesRouteApiMatchIsotopesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateMatchIsotopesRouteApiMatchIsotopesPost.Responses.$200>
  /**
   * delete_match_isotopes_route_api_match_isotopes_delete - Delete Match Isotopes Route
   */
  'delete_match_isotopes_route_api_match_isotopes_delete'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.DeleteMatchIsotopesRouteApiMatchIsotopesDelete.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteMatchIsotopesRouteApiMatchIsotopesDelete.Responses.$200>
  /**
   * get_match_isotope_route_api_match_isotopes__match_isotope_id__get - Get Match Isotope Route
   */
  'get_match_isotope_route_api_match_isotopes__match_isotope_id__get'(
    parameters?: Parameters<Paths.GetMatchIsotopeRouteApiMatchIsotopesMatchIsotopeIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchIsotopeRouteApiMatchIsotopesMatchIsotopeIdGet.Responses.$200>
  /**
   * get_match_sample_collections_route_api_match_targets_sample__sample_item_id__collections_get - Get Match Sample Collections Route
   */
  'get_match_sample_collections_route_api_match_targets_sample__sample_item_id__collections_get'(
    parameters?: Parameters<Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.QueryParameters & Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.Responses.$200>
  /**
   * get_match_sample_compounds_route_api_match_targets_sample__sample_item_id__compounds_get - Get Match Sample Compounds Route
   */
  'get_match_sample_compounds_route_api_match_targets_sample__sample_item_id__compounds_get'(
    parameters?: Parameters<Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.QueryParameters & Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.Responses.$200>
  /**
   * get_match_sample_ions_route_api_match_targets_sample__sample_item_id__ions_get - Get Match Sample Ions Route
   */
  'get_match_sample_ions_route_api_match_targets_sample__sample_item_id__ions_get'(
    parameters?: Parameters<Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.QueryParameters & Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.Responses.$200>
  /**
   * get_match_sample_isotopes_route_api_match_targets_sample__sample_item_id__isotopes_get - Get Match Sample Isotopes Route
   */
  'get_match_sample_isotopes_route_api_match_targets_sample__sample_item_id__isotopes_get'(
    parameters?: Parameters<Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.QueryParameters & Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.Responses.$200>
  /**
   * get_batch_data_route_api_match_targets_batch__sample_batch_id__get - Get Batch Data Route
   */
  'get_batch_data_route_api_match_targets_batch__sample_batch_id__get'(
    parameters?: Parameters<Paths.GetBatchDataRouteApiMatchTargetsBatchSampleBatchIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetBatchDataRouteApiMatchTargetsBatchSampleBatchIdGet.Responses.$200>
  /**
   * get_match_batch_collections_route_api_match_targets_batch__sample_batch_id__collections_get - Get Match Batch Collections Route
   */
  'get_match_batch_collections_route_api_match_targets_batch__sample_batch_id__collections_get'(
    parameters?: Parameters<Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.QueryParameters & Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.Responses.$200>
  /**
   * get_match_batch_compounds_route_api_match_targets_batch__sample_batch_id__compounds_get - Get Match Batch Compounds Route
   */
  'get_match_batch_compounds_route_api_match_targets_batch__sample_batch_id__compounds_get'(
    parameters?: Parameters<Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.QueryParameters & Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.Responses.$200>
  /**
   * get_match_batch_ions_route_api_match_targets_batch__sample_batch_id__ions_get - Get Match Batch Ions Route
   */
  'get_match_batch_ions_route_api_match_targets_batch__sample_batch_id__ions_get'(
    parameters?: Parameters<Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.QueryParameters & Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.Responses.$200>
  /**
   * get_match_batch_isotopes_route_api_match_targets_batch__sample_batch_id__isotopes_get - Get Match Batch Isotopes Route
   */
  'get_match_batch_isotopes_route_api_match_targets_batch__sample_batch_id__isotopes_get'(
    parameters?: Parameters<Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.QueryParameters & Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.Responses.$200>
  /**
   * get_attribute_templates_route_api_attribute_templates_get - Get Attribute Templates Route
   */
  'get_attribute_templates_route_api_attribute_templates_get'(
    parameters?: Parameters<Paths.GetAttributeTemplatesRouteApiAttributeTemplatesGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetAttributeTemplatesRouteApiAttributeTemplatesGet.Responses.$200>
  /**
   * create_attribute_template_route_api_attribute_templates_post - Create Attribute Template Route
   */
  'create_attribute_template_route_api_attribute_templates_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateAttributeTemplateRouteApiAttributeTemplatesPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateAttributeTemplateRouteApiAttributeTemplatesPost.Responses.$200>
  /**
   * get_attribute_template_route_api_attribute_templates__attribute_template_id__get - Get Attribute Template Route
   */
  'get_attribute_template_route_api_attribute_templates__attribute_template_id__get'(
    parameters?: Parameters<Paths.GetAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdGet.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdGet.Responses.$200>
  /**
   * update_attribute_template_route_api_attribute_templates__attribute_template_id__patch - Update Attribute Template Route
   */
  'update_attribute_template_route_api_attribute_templates__attribute_template_id__patch'(
    parameters?: Parameters<Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.PathParameters> | null,
    data?: Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.Responses.$200>
  /**
   * delete_attribute_template_route_api_attribute_templates__attribute_template_id__delete - Delete Attribute Template Route
   */
  'delete_attribute_template_route_api_attribute_templates__attribute_template_id__delete'(
    parameters?: Parameters<Paths.DeleteAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdDelete.Responses.$200>
  /**
   * get_instrument_functions_route_api_instrument_functions_get - Get Instrument Functions Route
   */
  'get_instrument_functions_route_api_instrument_functions_get'(
    parameters?: Parameters<Paths.GetInstrumentFunctionsRouteApiInstrumentFunctionsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetInstrumentFunctionsRouteApiInstrumentFunctionsGet.Responses.$200>
  /**
   * create_instrument_function_route_api_instrument_functions_post - Create Instrument Function Route
   */
  'create_instrument_function_route_api_instrument_functions_post'(
    parameters?: Parameters<UnknownParamsObject> | null,
    data?: Paths.CreateInstrumentFunctionRouteApiInstrumentFunctionsPost.RequestBody,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.CreateInstrumentFunctionRouteApiInstrumentFunctionsPost.Responses.$200>
  /**
   * get_instrument_function_route_api_instrument_functions__get - Get Instrument Function Route
   */
  'get_instrument_function_route_api_instrument_functions__get'(
    parameters?: Parameters<Paths.GetInstrumentFunctionRouteApiInstrumentFunctionsGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.GetInstrumentFunctionRouteApiInstrumentFunctionsGet.Responses.$200>
  /**
   * delete_instrument_function_route_api_instrument_functions__instrument_function_id__delete - Delete Instrument Function Route
   */
  'delete_instrument_function_route_api_instrument_functions__instrument_function_id__delete'(
    parameters?: Parameters<Paths.DeleteInstrumentFunctionRouteApiInstrumentFunctionsInstrumentFunctionIdDelete.PathParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.DeleteInstrumentFunctionRouteApiInstrumentFunctionsInstrumentFunctionIdDelete.Responses.$200>
  /**
   * visualization_ion_focus_route_api_visualization_ion_focus_get - Visualization Ion Focus Route
   */
  'visualization_ion_focus_route_api_visualization_ion_focus_get'(
    parameters?: Parameters<Paths.VisualizationIonFocusRouteApiVisualizationIonFocusGet.QueryParameters> | null,
    data?: any,
    config?: AxiosRequestConfig  
  ): OperationResponse<Paths.VisualizationIonFocusRouteApiVisualizationIonFocusGet.Responses.$200>
}

export interface PathsDictionary {
  ['/api/auth/login']: {
    /**
     * auth_jwt_login_api_auth_login_post - Auth:Jwt.Login
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.AuthJwtLoginApiAuthLoginPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AuthJwtLoginApiAuthLoginPost.Responses.$200 | Paths.AuthJwtLoginApiAuthLoginPost.Responses.$204>
  }
  ['/api/auth/logout']: {
    /**
     * auth_jwt_logout_api_auth_logout_post - Auth:Jwt.Logout
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AuthJwtLogoutApiAuthLogoutPost.Responses.$200 | Paths.AuthJwtLogoutApiAuthLogoutPost.Responses.$204>
  }
  ['/api/auth/register']: {
    /**
     * register_register_api_auth_register_post - Register:Register
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.RegisterRegisterApiAuthRegisterPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.RegisterRegisterApiAuthRegisterPost.Responses.$201>
  }
  ['/api/users/me']: {
    /**
     * users_current_user_api_users_me_get - Users:Current User
     */
    'get'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UsersCurrentUserApiUsersMeGet.Responses.$200>
    /**
     * users_patch_current_user_api_users_me_patch - Users:Patch Current User
     */
    'patch'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.UsersPatchCurrentUserApiUsersMePatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UsersPatchCurrentUserApiUsersMePatch.Responses.$200>
  }
  ['/api/users/{id}']: {
    /**
     * users_user_api_users__id__get - Users:User
     */
    'get'(
      parameters?: Parameters<Paths.UsersUserApiUsersIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UsersUserApiUsersIdGet.Responses.$200>
    /**
     * users_patch_user_api_users__id__patch - Users:Patch User
     */
    'patch'(
      parameters?: Parameters<Paths.UsersPatchUserApiUsersIdPatch.PathParameters> | null,
      data?: Paths.UsersPatchUserApiUsersIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UsersPatchUserApiUsersIdPatch.Responses.$200>
    /**
     * users_delete_user_api_users__id__delete - Users:Delete User
     */
    'delete'(
      parameters?: Parameters<Paths.UsersDeleteUserApiUsersIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UsersDeleteUserApiUsersIdDelete.Responses.$204>
  }
  ['/api/workspaces']: {
    /**
     * get_workspaces_route_api_workspaces_get - Get Workspaces Route
     */
    'get'(
      parameters?: Parameters<Paths.GetWorkspacesRouteApiWorkspacesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetWorkspacesRouteApiWorkspacesGet.Responses.$200>
    /**
     * create_workspace_route_api_workspaces_post - Create Workspace Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateWorkspaceRouteApiWorkspacesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateWorkspaceRouteApiWorkspacesPost.Responses.$200>
  }
  ['/api/workspaces/{workspace_id}']: {
    /**
     * get_workspace_route_api_workspaces__workspace_id__get - Get Workspace Route
     */
    'get'(
      parameters?: Parameters<Paths.GetWorkspaceRouteApiWorkspacesWorkspaceIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetWorkspaceRouteApiWorkspacesWorkspaceIdGet.Responses.$200>
    /**
     * update_workspace_route_api_workspaces__workspace_id__patch - Update Workspace Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.PathParameters> | null,
      data?: Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateWorkspaceRouteApiWorkspacesWorkspaceIdPatch.Responses.$200>
    /**
     * delete_workspace_route_api_workspaces__workspace_id__delete - Delete Workspace Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteWorkspaceRouteApiWorkspacesWorkspaceIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteWorkspaceRouteApiWorkspacesWorkspaceIdDelete.Responses.$200>
  }
  ['/api/workspaces/{workspace_id}/protected']: {
    /**
     * get_workspace_protected_route_api_workspaces__workspace_id__protected_get - Get Workspace Protected Route
     */
    'get'(
      parameters?: Parameters<Paths.GetWorkspaceProtectedRouteApiWorkspacesWorkspaceIdProtectedGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetWorkspaceProtectedRouteApiWorkspacesWorkspaceIdProtectedGet.Responses.$200>
  }
  ['/api/workspaces/{workspace_id}/admin']: {
    /**
     * get_workspace_admin_route_api_workspaces__workspace_id__admin_get - Get Workspace Admin Route
     */
    'get'(
      parameters?: Parameters<Paths.GetWorkspaceAdminRouteApiWorkspacesWorkspaceIdAdminGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetWorkspaceAdminRouteApiWorkspacesWorkspaceIdAdminGet.Responses.$200>
  }
  ['/api/sample/batches']: {
    /**
     * get_sample_batches_route_api_sample_batches_get - Get Sample Batches Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleBatchesRouteApiSampleBatchesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleBatchesRouteApiSampleBatchesGet.Responses.$200>
    /**
     * create_sample_batch_route_api_sample_batches_post - Create Sample Batch Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateSampleBatchRouteApiSampleBatchesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateSampleBatchRouteApiSampleBatchesPost.Responses.$200>
  }
  ['/api/sample/batches/{sample_batch_id}']: {
    /**
     * get_sample_batch_route_api_sample_batches__sample_batch_id__get - Get Sample Batch Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleBatchRouteApiSampleBatchesSampleBatchIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleBatchRouteApiSampleBatchesSampleBatchIdGet.Responses.$200>
    /**
     * update_sample_batch_route_api_sample_batches__sample_batch_id__patch - Update Sample Batch Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.PathParameters> | null,
      data?: Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateSampleBatchRouteApiSampleBatchesSampleBatchIdPatch.Responses.$200>
    /**
     * delete_sample_batch_route_api_sample_batches__sample_batch_id__delete - Delete Sample Batch Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteSampleBatchRouteApiSampleBatchesSampleBatchIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteSampleBatchRouteApiSampleBatchesSampleBatchIdDelete.Responses.$200>
  }
  ['/api/sample/batches/{sample_batch_id}/targets']: {
    /**
     * get_batch_targets_route_api_sample_batches__sample_batch_id__targets_get - Get Batch Targets Route
     */
    'get'(
      parameters?: Parameters<Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.QueryParameters & Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetBatchTargetsRouteApiSampleBatchesSampleBatchIdTargetsGet.Responses.$200>
  }
  ['/api/sample/batches/{sample_batch_id}/import']: {
    /**
     * import_sample_items_route_api_sample_batches__sample_batch_id__import_post - Import Sample Items Route
     */
    'post'(
      parameters?: Parameters<Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.PathParameters> | null,
      data?: Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.ImportSampleItemsRouteApiSampleBatchesSampleBatchIdImportPost.Responses.$200>
  }
  ['/api/sample/batches/{sample_batch_id}/copy']: {
    /**
     * copy_sample_batch_route_api_sample_batches__sample_batch_id__copy_post - Copy Sample Batch Route
     */
    'post'(
      parameters?: Parameters<Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.PathParameters> | null,
      data?: Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CopySampleBatchRouteApiSampleBatchesSampleBatchIdCopyPost.Responses.$200>
  }
  ['/api/sample/batches/{sample_batch_id}/export_peaks']: {
    /**
     * sample_batch_export_peaks_route_api_sample_batches__sample_batch_id__export_peaks_get - Sample Batch Export Peaks Route
     */
    'get'(
      parameters?: Parameters<Paths.SampleBatchExportPeaksRouteApiSampleBatchesSampleBatchIdExportPeaksGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.SampleBatchExportPeaksRouteApiSampleBatchesSampleBatchIdExportPeaksGet.Responses.$200>
  }
  ['/api/samples']: {
    /**
     * get_samples_route_api_samples_get - Get Samples Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSamplesRouteApiSamplesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSamplesRouteApiSamplesGet.Responses.$200>
  }
  ['/api/samples/{sample_item_id}']: {
    /**
     * get_sample_route_api_samples__sample_item_id__get - Get Sample Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleRouteApiSamplesSampleItemIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleRouteApiSamplesSampleItemIdGet.Responses.$200>
  }
  ['/api/sample/items']: {
    /**
     * get_sample_items_route_api_sample_items_get - Get Sample Items Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleItemsRouteApiSampleItemsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleItemsRouteApiSampleItemsGet.Responses.$200>
    /**
     * create_sample_item_route_api_sample_items_post - Create Sample Item Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateSampleItemRouteApiSampleItemsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateSampleItemRouteApiSampleItemsPost.Responses.$200>
  }
  ['/api/sample/items/{sample_item_id}']: {
    /**
     * get_sample_item_route_api_sample_items__sample_item_id__get - Get Sample Item Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleItemRouteApiSampleItemsSampleItemIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleItemRouteApiSampleItemsSampleItemIdGet.Responses.$200>
    /**
     * update_sample_item_route_api_sample_items__sample_item_id__patch - Update Sample Item Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.PathParameters> | null,
      data?: Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateSampleItemRouteApiSampleItemsSampleItemIdPatch.Responses.$200>
    /**
     * delete_sample_item_route_api_sample_items__sample_item_id__delete - Delete Sample Item Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteSampleItemRouteApiSampleItemsSampleItemIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteSampleItemRouteApiSampleItemsSampleItemIdDelete.Responses.$200>
  }
  ['/api/sample/items/{sample_item_id}/copy']: {
    /**
     * copy_sample_item_route_api_sample_items__sample_item_id__copy_post - Copy Sample Item Route
     */
    'post'(
      parameters?: Parameters<Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.PathParameters> | null,
      data?: Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CopySampleItemRouteApiSampleItemsSampleItemIdCopyPost.Responses.$200>
  }
  ['/api/sample/items/process']: {
    /**
     * process_sample_item_route_api_sample_items_process_post - Process Sample Item Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.ProcessSampleItemRouteApiSampleItemsProcessPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.ProcessSampleItemRouteApiSampleItemsProcessPost.Responses.$200>
  }
  ['/api/sample/files']: {
    /**
     * get_sample_files_route_api_sample_files_get - Get Sample Files Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleFilesRouteApiSampleFilesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleFilesRouteApiSampleFilesGet.Responses.$200>
    /**
     * create_sample_file_route_api_sample_files_post - Create Sample File Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateSampleFileRouteApiSampleFilesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateSampleFileRouteApiSampleFilesPost.Responses.$200>
  }
  ['/api/sample/files/recent']: {
    /**
     * get_recent_sample_files_route_api_sample_files_recent_get - Get Recent Sample Files Route
     */
    'get'(
      parameters?: Parameters<Paths.GetRecentSampleFilesRouteApiSampleFilesRecentGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetRecentSampleFilesRouteApiSampleFilesRecentGet.Responses.$200>
  }
  ['/api/sample/files/{sample_file_id}']: {
    /**
     * get_sample_file_route_api_sample_files__sample_file_id__get - Get Sample File Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleFileRouteApiSampleFilesSampleFileIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleFileRouteApiSampleFilesSampleFileIdGet.Responses.$200>
    /**
     * update_sample_file_route_api_sample_files__sample_file_id__patch - Update Sample File Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.PathParameters> | null,
      data?: Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateSampleFileRouteApiSampleFilesSampleFileIdPatch.Responses.$200>
    /**
     * delete_sample_file_route_api_sample_files__sample_file_id__delete - Delete Sample File Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteSampleFileRouteApiSampleFilesSampleFileIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteSampleFileRouteApiSampleFilesSampleFileIdDelete.Responses.$200>
  }
  ['/api/sample/files/{sample_file_id}/peaks']: {
    /**
     * get_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_get - Get Sample File Peaks Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.QueryParameters & Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksGet.Responses.$200>
  }
  ['/api/sample/files/{sample_file_id}/peaks/compute']: {
    /**
     * compute_all_sample_file_peaks_route_api_sample_files__sample_file_id__peaks_compute_get - Compute All Sample File Peaks Route
     */
    'get'(
      parameters?: Parameters<Paths.ComputeAllSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksComputeGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.ComputeAllSampleFilePeaksRouteApiSampleFilesSampleFileIdPeaksComputeGet.Responses.$200>
  }
  ['/api/sample/files/{sample_file_id}/peaks/timeseries']: {
    /**
     * get_sample_file_peak_timeseries_route_api_sample_files__sample_file_id__peaks_timeseries_post - Get Sample File Peak Timeseries Route
     */
    'post'(
      parameters?: Parameters<Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.PathParameters> | null,
      data?: Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleFilePeakTimeseriesRouteApiSampleFilesSampleFileIdPeaksTimeseriesPost.Responses.$200>
  }
  ['/api/sample/files/{sample_file_id}/spectrum']: {
    /**
     * get_sample_file_spectrum_route_api_sample_files__sample_file_id__spectrum_get - Get Sample File Spectrum Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.QueryParameters & Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleFileSpectrumRouteApiSampleFilesSampleFileIdSpectrumGet.Responses.$200>
  }
  ['/api/sample/files/upload']: {
    /**
     * sample_file_upload_route_api_sample_files_upload_post - Sample File Upload Route
     * 
     * Uploads a sample file to the server.
     * 
     * This route takes an uploaded file from a form field and saves it in the `filestreams` directory
     * on the server. It validates the file's size and extension before uploading.
     * 
     * :param file: The file to be uploaded, provided in a form field.
     * :type file: UploadFile
     * :return: A JSON response indicating the success or failure of the upload.
     * :rtype: JSONResponse
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.SampleFileUploadRouteApiSampleFilesUploadPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.SampleFileUploadRouteApiSampleFilesUploadPost.Responses.$200>
  }
  ['/api/calibration/mz_calibration']: {
    /**
     * get_sample_mz_calibration_route_api_calibration_mz_calibration_get - Get Sample Mz Calibration Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleMzCalibrationRouteApiCalibrationMzCalibrationGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleMzCalibrationRouteApiCalibrationMzCalibrationGet.Responses.$200>
  }
  ['/api/calibration/mz_fit']: {
    /**
     * calibration_mz_fit_route_api_calibration_mz_fit_post - Calibration Mz Fit Route
     */
    'post'(
      parameters?: Parameters<Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.QueryParameters> | null,
      data?: Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CalibrationMzFitRouteApiCalibrationMzFitPost.Responses.$200>
  }
  ['/api/calibration/mz_apply']: {
    /**
     * calibration_mz_apply_route_api_calibration_mz_apply_post - Calibration Mz Apply Route
     */
    'post'(
      parameters?: Parameters<Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.QueryParameters> | null,
      data?: Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CalibrationMzApplyRouteApiCalibrationMzApplyPost.Responses.$200>
  }
  ['/api/calibration/mz_calibrate/sample/{sample_item_id}']: {
    /**
     * calibration_mz_calibrate_sample_route_api_calibration_mz_calibrate_sample__sample_item_id__post - Calibration Mz Calibrate Sample Route
     */
    'post'(
      parameters?: Parameters<Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.PathParameters> | null,
      data?: Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CalibrationMzCalibrateSampleRouteApiCalibrationMzCalibrateSampleSampleItemIdPost.Responses.$200>
  }
  ['/api/calibration/mz_calibrate/batch/{sample_batch_id}']: {
    /**
     * calibration_mz_calibrate_batch_route_api_calibration_mz_calibrate_batch__sample_batch_id__post - Calibration Mz Calibrate Batch Route
     */
    'post'(
      parameters?: Parameters<Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.PathParameters> | null,
      data?: Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CalibrationMzCalibrateBatchRouteApiCalibrationMzCalibrateBatchSampleBatchIdPost.Responses.$200>
  }
  ['/api/target/collections']: {
    /**
     * get_target_collections_route_api_target_collections_get - Get Target Collections Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCollectionsRouteApiTargetCollectionsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCollectionsRouteApiTargetCollectionsGet.Responses.$200>
    /**
     * create_target_collection_route_api_target_collections_post - Create Target Collection Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateTargetCollectionRouteApiTargetCollectionsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateTargetCollectionRouteApiTargetCollectionsPost.Responses.$200>
  }
  ['/api/target/collections/{target_collection_id}']: {
    /**
     * get_target_collection_route_api_target_collections__target_collection_id__get - Get Target Collection Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCollectionRouteApiTargetCollectionsTargetCollectionIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCollectionRouteApiTargetCollectionsTargetCollectionIdGet.Responses.$200>
    /**
     * update_target_collection_route_api_target_collections__target_collection_id__patch - Update Target Collection Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.PathParameters> | null,
      data?: Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateTargetCollectionRouteApiTargetCollectionsTargetCollectionIdPatch.Responses.$200>
    /**
     * delete_target_collection_route_api_target_collections__target_collection_id__delete - Delete Target Collection Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.QueryParameters & Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteTargetCollectionRouteApiTargetCollectionsTargetCollectionIdDelete.Responses.$200>
  }
  ['/api/target/associations/target_collections_in_sample_batch']: {
    /**
     * get_target_collections_in_sample_batch_route_api_target_associations_target_collections_in_sample_batch_get - Get Target Collections In Sample Batch Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCollectionsInSampleBatchRouteApiTargetAssociationsTargetCollectionsInSampleBatchGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCollectionsInSampleBatchRouteApiTargetAssociationsTargetCollectionsInSampleBatchGet.Responses.$200>
  }
  ['/api/target/compounds']: {
    /**
     * get_target_compounds_route_api_target_compounds_get - Get Target Compounds Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCompoundsRouteApiTargetCompoundsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCompoundsRouteApiTargetCompoundsGet.Responses.$200>
    /**
     * create_target_compounds_route_api_target_compounds_post - Create Target Compounds Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateTargetCompoundsRouteApiTargetCompoundsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateTargetCompoundsRouteApiTargetCompoundsPost.Responses.$200>
    /**
     * update_target_compound_route_api_target_compounds_patch - Update Target Compound Route
     */
    'patch'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.UpdateTargetCompoundRouteApiTargetCompoundsPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateTargetCompoundRouteApiTargetCompoundsPatch.Responses.$200>
  }
  ['/api/target/compounds/{target_compound_id}']: {
    /**
     * get_target_compound_route_api_target_compounds__target_compound_id__get - Get Target Compound Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCompoundRouteApiTargetCompoundsTargetCompoundIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCompoundRouteApiTargetCompoundsTargetCompoundIdGet.Responses.$200>
    /**
     * delete_target_compound_route_api_target_compounds__target_compound_id__delete - Delete Target Compound Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteTargetCompoundRouteApiTargetCompoundsTargetCompoundIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteTargetCompoundRouteApiTargetCompoundsTargetCompoundIdDelete.Responses.$200>
  }
  ['/api/target/associations/target_compound_in_target_collections']: {
    /**
     * get_target_compound_in_target_collections_route_api_target_associations_target_compound_in_target_collections_get - Get Target Compound In Target Collections Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetCompoundInTargetCollectionsRouteApiTargetAssociationsTargetCompoundInTargetCollectionsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetCompoundInTargetCollectionsRouteApiTargetAssociationsTargetCompoundInTargetCollectionsGet.Responses.$200>
  }
  ['/api/target/ions']: {
    /**
     * get_target_ions_route_api_target_ions_get - Get Target Ions Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetIonsRouteApiTargetIonsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetIonsRouteApiTargetIonsGet.Responses.$200>
  }
  ['/api/target/ions/{target_ion_id}']: {
    /**
     * get_target_ion_route_api_target_ions__target_ion_id__get - Get Target Ion Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetIonRouteApiTargetIonsTargetIonIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetIonRouteApiTargetIonsTargetIonIdGet.Responses.$200>
    /**
     * update_target_ion_route_api_target_ions__target_ion_id__patch - Update Target Ion Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.PathParameters> | null,
      data?: Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateTargetIonRouteApiTargetIonsTargetIonIdPatch.Responses.$200>
  }
  ['/api/ionization_mechanisms']: {
    /**
     * get_ionization_mechanisms_route_api_ionization_mechanisms_get - Get Ionization Mechanisms Route
     */
    'get'(
      parameters?: Parameters<Paths.GetIonizationMechanismsRouteApiIonizationMechanismsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetIonizationMechanismsRouteApiIonizationMechanismsGet.Responses.$200>
    /**
     * create_ionization_mechanism_route_api_ionization_mechanisms_post - Create Ionization Mechanism Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateIonizationMechanismRouteApiIonizationMechanismsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateIonizationMechanismRouteApiIonizationMechanismsPost.Responses.$200>
  }
  ['/api/ionization_mechanisms/{ionization_mechanism_id}']: {
    /**
     * get_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__get - Get Ionization Mechanism Route
     */
    'get'(
      parameters?: Parameters<Paths.GetIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdGet.Responses.$200>
    /**
     * delete_ionization_mechanism_route_api_ionization_mechanisms__ionization_mechanism_id__delete - Delete Ionization Mechanism Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteIonizationMechanismRouteApiIonizationMechanismsIonizationMechanismIdDelete.Responses.$200>
  }
  ['/api/target/isotopes']: {
    /**
     * get_target_isotopes_route_api_target_isotopes_get - Get Target Isotopes Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.QueryParameters> | null,
      data?: Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetIsotopesRouteApiTargetIsotopesGet.Responses.$200>
  }
  ['/api/target/isotopes/{target_isotope_id}']: {
    /**
     * get_target_isotope_route_api_target_isotopes__target_isotope_id__get - Get Target Isotope Route
     */
    'get'(
      parameters?: Parameters<Paths.GetTargetIsotopeRouteApiTargetIsotopesTargetIsotopeIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetTargetIsotopeRouteApiTargetIsotopesTargetIsotopeIdGet.Responses.$200>
  }
  ['/api/match/rematch/batches']: {
    /**
     * rematch_batches_route_api_match_rematch_batches_post - Rematch Batches Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.RematchBatchesRouteApiMatchRematchBatchesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.RematchBatchesRouteApiMatchRematchBatchesPost.Responses.$200>
  }
  ['/api/match/rematch/batch/{sample_batch_id}']: {
    /**
     * rematch_batch_route_api_match_rematch_batch__sample_batch_id__post - Rematch Batch Route
     */
    'post'(
      parameters?: Parameters<Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.PathParameters> | null,
      data?: Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.RematchBatchRouteApiMatchRematchBatchSampleBatchIdPost.Responses.$200>
  }
  ['/api/match/compute/batch/{sample_batch_id}']: {
    /**
     * match_compute_batch_route_api_match_compute_batch__sample_batch_id__post - Match Compute Batch Route
     */
    'post'(
      parameters?: Parameters<Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.PathParameters> | null,
      data?: Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.MatchComputeBatchRouteApiMatchComputeBatchSampleBatchIdPost.Responses.$200>
  }
  ['/api/match/remove/batch/{sample_batch_id}']: {
    /**
     * match_remove_batch_route_api_match_remove_batch__sample_batch_id__delete - Match Remove Batch Route
     */
    'delete'(
      parameters?: Parameters<Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.PathParameters> | null,
      data?: Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.MatchRemoveBatchRouteApiMatchRemoveBatchSampleBatchIdDelete.Responses.$200>
  }
  ['/api/match/rematch/sample/{sample_item_id}']: {
    /**
     * rematch_sample_route_api_match_rematch_sample__sample_item_id__post - Rematch Sample Route
     */
    'post'(
      parameters?: Parameters<Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.PathParameters> | null,
      data?: Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.RematchSampleRouteApiMatchRematchSampleSampleItemIdPost.Responses.$200>
  }
  ['/api/match/remove/sample/{sample_item_id}']: {
    /**
     * match_remove_sample_route_api_match_remove_sample__sample_item_id__delete - Match Remove Sample Route
     */
    'delete'(
      parameters?: Parameters<Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.PathParameters> | null,
      data?: Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.MatchRemoveSampleRouteApiMatchRemoveSampleSampleItemIdDelete.Responses.$200>
  }
  ['/api/match/compute/sample/{sample_item_id}']: {
    /**
     * match_compute_sample_route_api_match_compute_sample__sample_item_id__post - Match Compute Sample Route
     */
    'post'(
      parameters?: Parameters<Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.PathParameters> | null,
      data?: Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.MatchComputeSampleRouteApiMatchComputeSampleSampleItemIdPost.Responses.$200>
  }
  ['/api/match/remove/all']: {
    /**
     * match_remove_all_route_api_match_remove_all_delete - Match Remove All Route
     * 
     * Endpoint to delete all match data across the system.
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.MatchRemoveAllRouteApiMatchRemoveAllDelete.Responses.$200>
  }
  ['/api/match/aggregate/batch/{sample_batch_id}/isotope']: {
    /**
     * aggregate_batch_match_isotope_filtered_data_route_api_match_aggregate_batch__sample_batch_id__isotope_post - Aggregate Batch Match Isotope Filtered Data Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.PathParameters> | null,
      data?: Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateBatchMatchIsotopeFilteredDataRouteApiMatchAggregateBatchSampleBatchIdIsotopePost.Responses.$200>
  }
  ['/api/match/aggregate/batch/{sample_batch_id}']: {
    /**
     * aggregate_batch_matches_route_api_match_aggregate_batch__sample_batch_id__post - Aggregate Batch Matches Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.PathParameters> | null,
      data?: Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdPost.Responses.$200>
  }
  ['/api/match/aggregate/batch/{sample_batch_id}/save']: {
    /**
     * aggregate_and_create_batch_matches_route_api_match_aggregate_batch__sample_batch_id__save_post - Aggregate And Create Batch Matches Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.PathParameters> | null,
      data?: Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateAndCreateBatchMatchesRouteApiMatchAggregateBatchSampleBatchIdSavePost.Responses.$200>
  }
  ['/api/match/aggregate/batch/{sample_batch_id}/resave']: {
    /**
     * aggregate_and_recreate_matches_route_api_match_aggregate_batch__sample_batch_id__resave_post - Aggregate And Recreate Matches Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.PathParameters> | null,
      data?: Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateAndRecreateMatchesRouteApiMatchAggregateBatchSampleBatchIdResavePost.Responses.$200>
  }
  ['/api/match/aggregate/batch/{sample_batch_id}/all']: {
    /**
     * get_batch_and_aggregated_matches_route_api_match_aggregate_batch__sample_batch_id__all_get - Get Batch And Aggregated Matches Route
     */
    'get'(
      parameters?: Parameters<Paths.GetBatchAndAggregatedMatchesRouteApiMatchAggregateBatchSampleBatchIdAllGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetBatchAndAggregatedMatchesRouteApiMatchAggregateBatchSampleBatchIdAllGet.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}/isotope']: {
    /**
     * aggregate_sample_match_isotope_filtered_data_route_api_match_aggregate_sample__sample_item_id__isotope_post - Aggregate Sample Match Isotope Filtered Data Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.PathParameters> | null,
      data?: Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateSampleMatchIsotopeFilteredDataRouteApiMatchAggregateSampleSampleItemIdIsotopePost.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}/ion']: {
    /**
     * aggregate_sample_match_ion_route_api_match_aggregate_sample__sample_item_id__ion_post - Aggregate Sample Match Ion Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.PathParameters> | null,
      data?: Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateSampleMatchIonRouteApiMatchAggregateSampleSampleItemIdIonPost.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}/compound']: {
    /**
     * aggregate_sample_match_compound_route_api_match_aggregate_sample__sample_item_id__compound_post - Aggregate Sample Match Compound Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.PathParameters> | null,
      data?: Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateSampleMatchCompoundRouteApiMatchAggregateSampleSampleItemIdCompoundPost.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}']: {
    /**
     * aggregate_sample_matches_route_api_match_aggregate_sample__sample_item_id__post - Aggregate Sample Matches Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.PathParameters> | null,
      data?: Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdPost.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}/save']: {
    /**
     * aggregate_and_create_sample_matches_route_api_match_aggregate_sample__sample_item_id__save_post - Aggregate And Create Sample Matches Route
     */
    'post'(
      parameters?: Parameters<Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.PathParameters> | null,
      data?: Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.AggregateAndCreateSampleMatchesRouteApiMatchAggregateSampleSampleItemIdSavePost.Responses.$200>
  }
  ['/api/match/aggregate/sample/{sample_item_id}/all']: {
    /**
     * get_sample_aggregate_matches_route_api_match_aggregate_sample__sample_item_id__all_get - Get Sample Aggregate Matches Route
     */
    'get'(
      parameters?: Parameters<Paths.GetSampleAggregateMatchesRouteApiMatchAggregateSampleSampleItemIdAllGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetSampleAggregateMatchesRouteApiMatchAggregateSampleSampleItemIdAllGet.Responses.$200>
  }
  ['/api/match/samples']: {
    /**
     * get_match_samples_route_api_match_samples_get - Get Match Samples Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSamplesRouteApiMatchSamplesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSamplesRouteApiMatchSamplesGet.Responses.$200>
    /**
     * create_match_samples_route_api_match_samples_post - Create Match Samples Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchSamplesRouteApiMatchSamplesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchSamplesRouteApiMatchSamplesPost.Responses.$200>
    /**
     * delete_match_samples_route_api_match_samples_delete - Delete Match Samples Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchSamplesRouteApiMatchSamplesDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchSamplesRouteApiMatchSamplesDelete.Responses.$200>
  }
  ['/api/match/samples/{match_sample_id}']: {
    /**
     * get_match_sample_route_api_match_samples__match_sample_id__get - Get Match Sample Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSampleRouteApiMatchSamplesMatchSampleIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSampleRouteApiMatchSamplesMatchSampleIdGet.Responses.$200>
  }
  ['/api/match/collections']: {
    /**
     * get_match_collections_route_api_match_collections_get - Get Match Collections Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchCollectionsRouteApiMatchCollectionsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchCollectionsRouteApiMatchCollectionsGet.Responses.$200>
    /**
     * create_match_collections_route_api_match_collections_post - Create Match Collections Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchCollectionsRouteApiMatchCollectionsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchCollectionsRouteApiMatchCollectionsPost.Responses.$200>
    /**
     * delete_match_collections_route_api_match_collections_delete - Delete Match Collections Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchCollectionsRouteApiMatchCollectionsDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchCollectionsRouteApiMatchCollectionsDelete.Responses.$200>
  }
  ['/api/match/collections/{match_collection_id}']: {
    /**
     * get_match_collection_route_api_match_collections__match_collection_id__get - Get Match Collection Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchCollectionRouteApiMatchCollectionsMatchCollectionIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchCollectionRouteApiMatchCollectionsMatchCollectionIdGet.Responses.$200>
  }
  ['/api/match/compounds']: {
    /**
     * get_all_match_compounds_route_api_match_compounds_get - Get All Match Compounds Route
     */
    'get'(
      parameters?: Parameters<Paths.GetAllMatchCompoundsRouteApiMatchCompoundsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetAllMatchCompoundsRouteApiMatchCompoundsGet.Responses.$200>
    /**
     * create_match_compounds_route_api_match_compounds_post - Create Match Compounds Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchCompoundsRouteApiMatchCompoundsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchCompoundsRouteApiMatchCompoundsPost.Responses.$200>
    /**
     * delete_match_compounds_route_api_match_compounds_delete - Delete Match Compounds Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchCompoundsRouteApiMatchCompoundsDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchCompoundsRouteApiMatchCompoundsDelete.Responses.$200>
  }
  ['/api/match/compounds/{match_compound_id}']: {
    /**
     * get_match_compound_route_api_match_compounds__match_compound_id__get - Get Match Compound Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchCompoundRouteApiMatchCompoundsMatchCompoundIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchCompoundRouteApiMatchCompoundsMatchCompoundIdGet.Responses.$200>
  }
  ['/api/match/ions']: {
    /**
     * get_match_ions_route_api_match_ions_get - Get Match Ions Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchIonsRouteApiMatchIonsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchIonsRouteApiMatchIonsGet.Responses.$200>
    /**
     * create_match_ions_route_api_match_ions_post - Create Match Ions Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchIonsRouteApiMatchIonsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchIonsRouteApiMatchIonsPost.Responses.$200>
    /**
     * delete_match_ions_route_api_match_ions_delete - Delete Match Ions Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchIonsRouteApiMatchIonsDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchIonsRouteApiMatchIonsDelete.Responses.$200>
  }
  ['/api/match/ions/{match_ion_id}']: {
    /**
     * get_match_ion_route_api_match_ions__match_ion_id__get - Get Match Ion Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchIonRouteApiMatchIonsMatchIonIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchIonRouteApiMatchIonsMatchIonIdGet.Responses.$200>
  }
  ['/api/match_ratings']: {
    /**
     * get_match_ratings_route_api_match_ratings_get - Get Match Ratings Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchRatingsRouteApiMatchRatingsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchRatingsRouteApiMatchRatingsGet.Responses.$200>
    /**
     * create_match_rating_route_api_match_ratings_post - Create Match Rating Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchRatingRouteApiMatchRatingsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchRatingRouteApiMatchRatingsPost.Responses.$200>
  }
  ['/api/match_ratings/{match_rating_id}']: {
    /**
     * get_match_rating_route_api_match_ratings__match_rating_id__get - Get Match Rating Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchRatingRouteApiMatchRatingsMatchRatingIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchRatingRouteApiMatchRatingsMatchRatingIdGet.Responses.$200>
  }
  ['/api/match/interferences']: {
    /**
     * get_match_interferences_route_api_match_interferences_get - Get Match Interferences Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchInterferencesRouteApiMatchInterferencesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchInterferencesRouteApiMatchInterferencesGet.Responses.$200>
    /**
     * create_match_interferences_route_api_match_interferences_post - Create Match Interferences Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchInterferencesRouteApiMatchInterferencesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchInterferencesRouteApiMatchInterferencesPost.Responses.$200>
    /**
     * delete_match_interferences_route_api_match_interferences_delete - Delete Match Interferences Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchInterferencesRouteApiMatchInterferencesDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchInterferencesRouteApiMatchInterferencesDelete.Responses.$200>
  }
  ['/api/match/interferences/{match_interference_id}']: {
    /**
     * get_match_interference_route_api_match_interferences__match_interference_id__get - Get Match Interference Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchInterferenceRouteApiMatchInterferencesMatchInterferenceIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchInterferenceRouteApiMatchInterferencesMatchInterferenceIdGet.Responses.$200>
  }
  ['/api/match/isotopes']: {
    /**
     * get_match_isotopes_route_api_match_isotopes_get - Get Match Isotopes Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchIsotopesRouteApiMatchIsotopesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchIsotopesRouteApiMatchIsotopesGet.Responses.$200>
    /**
     * create_match_isotopes_route_api_match_isotopes_post - Create Match Isotopes Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateMatchIsotopesRouteApiMatchIsotopesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateMatchIsotopesRouteApiMatchIsotopesPost.Responses.$200>
    /**
     * delete_match_isotopes_route_api_match_isotopes_delete - Delete Match Isotopes Route
     */
    'delete'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.DeleteMatchIsotopesRouteApiMatchIsotopesDelete.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteMatchIsotopesRouteApiMatchIsotopesDelete.Responses.$200>
  }
  ['/api/match/isotopes/{match_isotope_id}']: {
    /**
     * get_match_isotope_route_api_match_isotopes__match_isotope_id__get - Get Match Isotope Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchIsotopeRouteApiMatchIsotopesMatchIsotopeIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchIsotopeRouteApiMatchIsotopesMatchIsotopeIdGet.Responses.$200>
  }
  ['/api/match/targets/sample/{sample_item_id}/collections']: {
    /**
     * get_match_sample_collections_route_api_match_targets_sample__sample_item_id__collections_get - Get Match Sample Collections Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.QueryParameters & Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSampleCollectionsRouteApiMatchTargetsSampleSampleItemIdCollectionsGet.Responses.$200>
  }
  ['/api/match/targets/sample/{sample_item_id}/compounds']: {
    /**
     * get_match_sample_compounds_route_api_match_targets_sample__sample_item_id__compounds_get - Get Match Sample Compounds Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.QueryParameters & Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSampleCompoundsRouteApiMatchTargetsSampleSampleItemIdCompoundsGet.Responses.$200>
  }
  ['/api/match/targets/sample/{sample_item_id}/ions']: {
    /**
     * get_match_sample_ions_route_api_match_targets_sample__sample_item_id__ions_get - Get Match Sample Ions Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.QueryParameters & Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSampleIonsRouteApiMatchTargetsSampleSampleItemIdIonsGet.Responses.$200>
  }
  ['/api/match/targets/sample/{sample_item_id}/isotopes']: {
    /**
     * get_match_sample_isotopes_route_api_match_targets_sample__sample_item_id__isotopes_get - Get Match Sample Isotopes Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.QueryParameters & Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchSampleIsotopesRouteApiMatchTargetsSampleSampleItemIdIsotopesGet.Responses.$200>
  }
  ['/api/match/targets/batch/{sample_batch_id}']: {
    /**
     * get_batch_data_route_api_match_targets_batch__sample_batch_id__get - Get Batch Data Route
     */
    'get'(
      parameters?: Parameters<Paths.GetBatchDataRouteApiMatchTargetsBatchSampleBatchIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetBatchDataRouteApiMatchTargetsBatchSampleBatchIdGet.Responses.$200>
  }
  ['/api/match/targets/batch/{sample_batch_id}/collections']: {
    /**
     * get_match_batch_collections_route_api_match_targets_batch__sample_batch_id__collections_get - Get Match Batch Collections Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.QueryParameters & Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchBatchCollectionsRouteApiMatchTargetsBatchSampleBatchIdCollectionsGet.Responses.$200>
  }
  ['/api/match/targets/batch/{sample_batch_id}/compounds']: {
    /**
     * get_match_batch_compounds_route_api_match_targets_batch__sample_batch_id__compounds_get - Get Match Batch Compounds Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.QueryParameters & Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchBatchCompoundsRouteApiMatchTargetsBatchSampleBatchIdCompoundsGet.Responses.$200>
  }
  ['/api/match/targets/batch/{sample_batch_id}/ions']: {
    /**
     * get_match_batch_ions_route_api_match_targets_batch__sample_batch_id__ions_get - Get Match Batch Ions Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.QueryParameters & Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchBatchIonsRouteApiMatchTargetsBatchSampleBatchIdIonsGet.Responses.$200>
  }
  ['/api/match/targets/batch/{sample_batch_id}/isotopes']: {
    /**
     * get_match_batch_isotopes_route_api_match_targets_batch__sample_batch_id__isotopes_get - Get Match Batch Isotopes Route
     */
    'get'(
      parameters?: Parameters<Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.QueryParameters & Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetMatchBatchIsotopesRouteApiMatchTargetsBatchSampleBatchIdIsotopesGet.Responses.$200>
  }
  ['/api/attribute_templates']: {
    /**
     * get_attribute_templates_route_api_attribute_templates_get - Get Attribute Templates Route
     */
    'get'(
      parameters?: Parameters<Paths.GetAttributeTemplatesRouteApiAttributeTemplatesGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetAttributeTemplatesRouteApiAttributeTemplatesGet.Responses.$200>
    /**
     * create_attribute_template_route_api_attribute_templates_post - Create Attribute Template Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateAttributeTemplateRouteApiAttributeTemplatesPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateAttributeTemplateRouteApiAttributeTemplatesPost.Responses.$200>
  }
  ['/api/attribute_templates/{attribute_template_id}']: {
    /**
     * get_attribute_template_route_api_attribute_templates__attribute_template_id__get - Get Attribute Template Route
     */
    'get'(
      parameters?: Parameters<Paths.GetAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdGet.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdGet.Responses.$200>
    /**
     * update_attribute_template_route_api_attribute_templates__attribute_template_id__patch - Update Attribute Template Route
     */
    'patch'(
      parameters?: Parameters<Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.PathParameters> | null,
      data?: Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.UpdateAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdPatch.Responses.$200>
    /**
     * delete_attribute_template_route_api_attribute_templates__attribute_template_id__delete - Delete Attribute Template Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteAttributeTemplateRouteApiAttributeTemplatesAttributeTemplateIdDelete.Responses.$200>
  }
  ['/api/instrument_functions']: {
    /**
     * get_instrument_functions_route_api_instrument_functions_get - Get Instrument Functions Route
     */
    'get'(
      parameters?: Parameters<Paths.GetInstrumentFunctionsRouteApiInstrumentFunctionsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetInstrumentFunctionsRouteApiInstrumentFunctionsGet.Responses.$200>
    /**
     * create_instrument_function_route_api_instrument_functions_post - Create Instrument Function Route
     */
    'post'(
      parameters?: Parameters<UnknownParamsObject> | null,
      data?: Paths.CreateInstrumentFunctionRouteApiInstrumentFunctionsPost.RequestBody,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.CreateInstrumentFunctionRouteApiInstrumentFunctionsPost.Responses.$200>
  }
  ['/api/instrument_functions/']: {
    /**
     * get_instrument_function_route_api_instrument_functions__get - Get Instrument Function Route
     */
    'get'(
      parameters?: Parameters<Paths.GetInstrumentFunctionRouteApiInstrumentFunctionsGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.GetInstrumentFunctionRouteApiInstrumentFunctionsGet.Responses.$200>
  }
  ['/api/instrument_functions/{instrument_function_id}']: {
    /**
     * delete_instrument_function_route_api_instrument_functions__instrument_function_id__delete - Delete Instrument Function Route
     */
    'delete'(
      parameters?: Parameters<Paths.DeleteInstrumentFunctionRouteApiInstrumentFunctionsInstrumentFunctionIdDelete.PathParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.DeleteInstrumentFunctionRouteApiInstrumentFunctionsInstrumentFunctionIdDelete.Responses.$200>
  }
  ['/api/visualization/ion_focus']: {
    /**
     * visualization_ion_focus_route_api_visualization_ion_focus_get - Visualization Ion Focus Route
     */
    'get'(
      parameters?: Parameters<Paths.VisualizationIonFocusRouteApiVisualizationIonFocusGet.QueryParameters> | null,
      data?: any,
      config?: AxiosRequestConfig  
    ): OperationResponse<Paths.VisualizationIonFocusRouteApiVisualizationIonFocusGet.Responses.$200>
  }
}

export type Client = OpenAPIClient<OperationMethods, PathsDictionary>

export type AggregateAndCreateMatchesBody = Components.Schemas.AggregateAndCreateMatchesBody;
export type AggregateMatchIsotopeFilteredDataBody = Components.Schemas.AggregateMatchIsotopeFilteredDataBody;
export type AggregateSampleMatchCompoundBody = Components.Schemas.AggregateSampleMatchCompoundBody;
export type AggregateSampleMatchIonBody = Components.Schemas.AggregateSampleMatchIonBody;
export type AttributeTemplateCreateBody = Components.Schemas.AttributeTemplateCreateBody;
export type AttributeTemplateUpdateBody = Components.Schemas.AttributeTemplateUpdateBody;
export type Body_auth_jwt_login_api_auth_login_post = Components.Schemas.BodyAuthJwtLoginApiAuthLoginPost;
export type Body_get_target_isotopes_route_api_target_isotopes_get = Components.Schemas.BodyGetTargetIsotopesRouteApiTargetIsotopesGet;
export type Body_sample_file_upload_route_api_sample_files_upload_post = Components.Schemas.BodySampleFileUploadRouteApiSampleFilesUploadPost;
export type BuildParams = Components.Schemas.BuildParams;
export type CalibrationMzApplyBody = Components.Schemas.CalibrationMzApplyBody;
export type DeleteMatchCollectionsPayload = Components.Schemas.DeleteMatchCollectionsPayload;
export type DeleteMatchCompounsPayload = Components.Schemas.DeleteMatchCompounsPayload;
export type DeleteMatchInterferencesPayload = Components.Schemas.DeleteMatchInterferencesPayload;
export type DeleteMatchIonsPayload = Components.Schemas.DeleteMatchIonsPayload;
export type DeleteMatchIsotopesPayload = Components.Schemas.DeleteMatchIsotopesPayload;
export type Environment = Components.Schemas.Environment;
export type ErrorModel = Components.Schemas.ErrorModel;
export type FilterParams = Components.Schemas.FilterParams;
export type FilterSamplePayload = Components.Schemas.FilterSamplePayload;
export type GetSampleFilePeakTimeseriesBody = Components.Schemas.GetSampleFilePeakTimeseriesBody;
export type HTTPValidationError = Components.Schemas.HTTPValidationError;
export type InstrumentFunctionCreateBody = Components.Schemas.InstrumentFunctionCreateBody;
export type IonizationMechanismCreate = Components.Schemas.IonizationMechanismCreate;
export type IsotopeRating = Components.Schemas.IsotopeRating;
export type MatchCollectionBase = Components.Schemas.MatchCollectionBase;
export type MatchCompoundBase = Components.Schemas.MatchCompoundBase;
export type MatchComputeBody = Components.Schemas.MatchComputeBody;
export type MatchInterferenceBase = Components.Schemas.MatchInterferenceBase;
export type MatchIonBase = Components.Schemas.MatchIonBase;
export type MatchIsotopeBase = Components.Schemas.MatchIsotopeBase;
export type MatchRatingChecklist = Components.Schemas.MatchRatingChecklist;
export type MatchRatingCreate = Components.Schemas.MatchRatingCreate;
export type MatchRemovePayload = Components.Schemas.MatchRemovePayload;
export type MatchSampleBase = Components.Schemas.MatchSampleBase;
export type MzCalibrationParams = Components.Schemas.MzCalibrationParams;
export type PeakShape = Components.Schemas.PeakShape;
export type RematchBatchBody = Components.Schemas.RematchBatchBody;
export type RematchBatchesBody = Components.Schemas.RematchBatchesBody;
export type RematchBody = Components.Schemas.RematchBody;
export type SampleBatchCopyBody = Components.Schemas.SampleBatchCopyBody;
export type SampleBatchCreateBody = Components.Schemas.SampleBatchCreateBody;
export type SampleBatchImportSamplesBody = Components.Schemas.SampleBatchImportSamplesBody;
export type SampleBatchUpdateBody = Components.Schemas.SampleBatchUpdateBody;
export type SampleFileCreate = Components.Schemas.SampleFileCreate;
export type SampleFileUpdate = Components.Schemas.SampleFileUpdate;
export type SampleItemCopyBody = Components.Schemas.SampleItemCopyBody;
export type SampleItemCreate = Components.Schemas.SampleItemCreate;
export type SampleItemProcessBody = Components.Schemas.SampleItemProcessBody;
export type SampleItemUpdate = Components.Schemas.SampleItemUpdate;
export type TargetCollectionCreateBody = Components.Schemas.TargetCollectionCreateBody;
export type TargetCollectionUpdateBody = Components.Schemas.TargetCollectionUpdateBody;
export type TargetCompoundBase = Components.Schemas.TargetCompoundBase;
export type TargetCompoundMatches = Components.Schemas.TargetCompoundMatches;
export type TargetCompoundUpdate = Components.Schemas.TargetCompoundUpdate;
export type TargetIonUpdate = Components.Schemas.TargetIonUpdate;
export type TemplateField = Components.Schemas.TemplateField;
export type UserCreate = Components.Schemas.UserCreate;
export type UserRead = Components.Schemas.UserRead;
export type UserUpdate = Components.Schemas.UserUpdate;
export type ValidationError = Components.Schemas.ValidationError;
export type WorkspaceCreate = Components.Schemas.WorkspaceCreate;
export type WorkspaceUpdate = Components.Schemas.WorkspaceUpdate;
