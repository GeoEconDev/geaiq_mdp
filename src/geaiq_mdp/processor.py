from __future__ import annotations
from itertools import product
from typing import TYPE_CHECKING
import logging
import os
import uuid as _uuid
from time import time
import pandas as pd
import numpy as np
from slugify import slugify
from uuid import UUID
import geopandas as gpd
from shapely import wkt
from functools import reduce

from geaiq_mdp.models.source import Point
from geaiq_mdp.models.wh import ObservableClass
from geaiq_mdp.process_logger import ProcessLogger

from .models import ObservableGroup, ObservableScale, Dimension, Period
from .models.utils import isref, resolve_unrefs_uuid, resolve_uuids, unref
from .timeout import timeout, TimeoutException
from .agg_op import MEASUREMENTUNIT_AGG_MAP
from .cache import cache, clean_cache
from .unit_types import MEASUREMENTUNIT_TYPE_MAP
from .geoecon_api import (
    GEOECON_API_MAP,
    GeoEconAPI,
    ObservableNotFound,
    DataError,
    GeoEconAPIError,
)
from .enums import (
    Environments,
    Encodings,
    GroupScaleEnum,
    MeasurementUnit,
    ObservableScaleTypeEnum,
    ObservableWithoutObservationActions,
)
from .report import Reportable, dump_df
from geaiq_mdp.geoecon_api import GeometryUploadingError
from .utils import (
    compare_dicts,
    es_legible_unicode,
    is_float,
    drop_duplicates,
    memory_time_logger,
)

if TYPE_CHECKING:
    from .models import Source, Column


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


class ProcessorError(Exception):
    message = None

    def __init__(self, *details):
        self.details = details

    def __str__(self):
        return f"{type(self).__name__}:{self.message}"

    def report(self):
        return {
            "typo": "error",
            "message": self.message or "No message",
            "details": self.details,
        }


class DuplicatedColumnNames(ProcessorError):
    message = "Duplicated columns in metadata"


class DuplicatedDataError(ProcessorError):
    message = "Duplicated observations"


class NoObservations(ProcessorError):
    message = "No observations"


class NoObservables(ProcessorError):
    message = "No observables"


class ObservationWithoutObservable(ProcessorError):
    message = "Observation without Observable"


class ColumnWithoutDefault(ProcessorError):
    message = "Using defaults for columns, but not all are defined"


class ObservableWithoutObservation(ProcessorError):
    message = "Observable without observation"


class FieldNotFound(ProcessorError):
    message = "Field not found"


class ObservationCastError(ProcessorError):
    message = "Observation casting error"


class QueryTooLarge(ProcessorError):
    message = "Query too large. Please reduce query size."


class QueryNotSolveAllColumns(ProcessorError):
    message = "Query does not solve all columns"


class QueryNotSolveAllRefColumns(ProcessorError):
    message = "Query does not solve all referenced columns"


class QueryOverrideComputedColumns(ProcessorError):
    message = "Query share columns with computed columns"


class ObservableScaleIssue(ProcessorError):
    message = "Observable scales issues"


class ObservableGroupNoPeriod(ProcessorError):
    message = "Observable group and/or period not defined"


class TopicsNotExists(ProcessorError):
    message = "Following topics does not exists"


class ColumnEvaluationError(ProcessorError):
    message = "Evaluation string error"


class UnsupportedGeometryType(ProcessorError):
    message = "Unsupported Geometry Type. Check with support the error."


class EncodingError(ProcessorError):
    message = "Can't read valid strings"


class Processor(Reportable):
    max_check_time_seconds = 36000
    max_agg_time_seconds = 36000

    @staticmethod
    def on_exception(f):
        def __inner__(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except ProcessorError as exc:
                logging.error(exc)
                self.message(**exc.report())
            except GeoEconAPIError as exc:
                logging.error(exc)
                self.message(**exc.report())
            return self.reset()

        return __inner__

    def __init__(self, error_retry=3):
        super().__init__()
        self.environment = None
        self.geoecon_api = None
        self.context = None
        self.error_retry = error_retry

    def setup(self, environment=None, context=None):
        if environment and not self.geoecon_api:
            self.environment = environment
            self.geoecon_api: GeoEconAPI = GEOECON_API_MAP[environment]()
        self.context = context

    def run_query(self, source: Source) -> pd.DataFrame:
        raise NotImplementedError

    def column_refs(
        self, source: Source, only_categorizables=False, accept_computables=True
    ):
        non_categorizables = (
            set(
                (
                    source.shape.id,
                    source.shape.parent_id,
                    source.shape.name,
                    source.shape.geometry if isref(source.shape.geometry) else None,
                    (
                        source.shape.geometry.latitude
                        if isinstance(source.shape.geometry, Point)
                        else None
                    ),
                    (
                        source.shape.geometry.longitude
                        if isinstance(source.shape.geometry, Point)
                        else None
                    ),
                )
            )
            if only_categorizables
            else set()
        )
        computables = (
            set(cr for cr in source.transform.data.compute.keys())
            if not accept_computables
            and source.transform
            and source.transform.data
            and source.transform.data.compute
            else set()
        )
        all_refs = set(source.column_refs())
        return list(
            cr.ref for cr in (all_refs - computables - non_categorizables - set([None]))
        )

    def do_source_encodings(self, source: Source, df: pd.DataFrame):
        return df.apply(
            lambda x: (
                x.str.encode(source.input_encoding.value).str.decode(
                    source.output_encoding.value
                )
                if x.dtype == "object"
                else x
            )
        )

    @cache(
        "read_source",
        lambda self, source: f"{source.slug}",
    )
    def read_source(self, source: Source) -> pd.DataFrame:
        column_names = [c.name for c in source.columns if c.eval is None]
        columns = {c.name: c for c in source.columns if c.eval is None}

        if len(columns.keys()) != len(column_names):
            raise DuplicatedColumnNames({"declared columns": column_names})

        cat_ref_columns = self.column_refs(
            source, only_categorizables=True, accept_computables=True
        )
        ref_columns = self.column_refs(
            source, only_categorizables=False, accept_computables=True
        )
        ignore_column_names = [source.shape.id.ref] if isref(source.shape.id) else []
        try:
            result = (
                self.run_query(source)
                .pipe(lambda df: self.do_source_encodings(source, df))
                .pipe(lambda df: self.do_source_transformation(source, df))
                .pipe(lambda df: self.do_source_selection(source, df))
                .pipe(
                    lambda df: (
                        df.rename(columns={source.shape.id.ref: "group_id"})
                        if isref(source.shape.id)
                        else df.assign(group_id=source.shape.id)
                    )
                )
                .astype({c: "category" for c in ["group_id"] + cat_ref_columns})
                .astype(
                    {c.name: MEASUREMENTUNIT_TYPE_MAP[c.unit] for c in columns.values()}
                )
            )[
                list(
                    set(
                        ["group_id"]
                        + column_names
                        + [
                            c
                            for c in ref_columns
                            if c and c not in column_names + ignore_column_names
                        ]
                    )
                )
            ]
        except KeyError as err:
            logging.warning("%s", err)
            if clean_cache("query", source.slug) and self.error_retry > 0:
                self.error_retry -= 1
                return self.read_source(source)
            else:
                raise err from err
        except ValueError as err:
            raise ObservationCastError(str(err))

        if isref(source.shape.geometry):
            self.info("Map", result[[source.shape.geometry.ref]])

        return result

    def stats(self, source: Source):
        data = self.read_source(source)
        if data is None or data.empty:
            return False

        total_rows = len(data.index)
        group_ids = data["group_id"]
        column_refs = data[self.column_refs(source, only_categorizables=True)]

        try:
            columns = (
                data[[c.name for c in source.columns if c.eval is None]]
                .astype(
                    {
                        c.name: (
                            float
                            if (
                                isinstance(
                                    MEASUREMENTUNIT_TYPE_MAP[c.unit],
                                    (pd.Int64Dtype, pd.Float64Dtype),
                                )
                                or MEASUREMENTUNIT_TYPE_MAP[c.unit] is float
                            )
                            else str
                        )
                        for c in source.columns
                        if c.eval is None
                    }
                )
                .astype(
                    {
                        c.name: MEASUREMENTUNIT_TYPE_MAP[c.unit]
                        for c in source.columns
                        if c.eval is None
                    }
                )
            )
        except (pd.errors.IntCastingNaNError, ValueError) as err:
            column = str(err).split("'")[-2]
            raise ObservationCastError(
                [
                    ("Error:", str(err)),
                    ("Data description", data[[column]].describe()),
                    ("Null rows", data[["group_id", column]][data[column].isnull()]),
                    (
                        "Error type values:",
                        data[["group_id", column]][~data[column].apply(is_float)],
                    ),
                ]
            )

        return [
            ("Row numbers", total_rows),
            (
                "Shape ID Describe",
                (
                    group_ids.describe(include=["O"])
                    if not group_ids.empty
                    else "No shapes"
                ),
            ),
            (
                "ColumnRef Describe",
                (
                    column_refs.describe()
                    if not column_refs.empty
                    else "No column reference"
                ),
            ),
            (
                "Columns Describe",
                (
                    (columns.describe() if not columns.empty else "No columns")
                    if total_rows > 1
                    else "Only for 2 or more rows"
                ),
            ),
        ]

    def warnings(self, source: Source):
        # AQUI HAY UN TEMA QUE RESOLVER
        data = self.read_source(source)
        if data is None or data.empty:
            return False

        if nan_cnt := len((null_group_ids := data[data["group_id"].isna()]).index):
            self.info("Data with Null group_id", null_group_ids)
            raise ObservationWithoutObservable(
                f"Nan values in observations: {nan_cnt} rows"
            )

        group_fields = ["group_id"] + self.column_refs(source, only_categorizables=True)
        group_colrefs_dup = data[data.duplicated(group_fields, keep=False)]
        if not group_colrefs_dup.empty:
            raise DuplicatedDataError(
                group_colrefs_dup.drop(
                    columns=(
                        [source.shape.geometry.ref]
                        if isref(source.shape.geometry)
                        else []
                    ),
                    errors="ignore",
                )
            )

        group_ids = data[["group_id"]]
        column_refs = data[self.column_refs(source, only_categorizables=True)]

        if group_ids.empty:
            raise NoObservations("Empty group_ids")
        elif column_refs.empty:
            self.info("No columnrefs required")
            return None

        group_id_describe = group_ids.describe()
        columnref_describe = column_refs.describe()

        shape_id_cnt = group_id_describe.loc["unique"]
        shape_column_stat = {
            v: int(column_refs[v].value_counts(dropna=True).sum())
            == int(shape_id_cnt.iloc[0])
            for v in columnref_describe
        }
        return {
            c: "The assignment of this column is not complete for all observables."
            for c, v in shape_column_stat.items()
            if v == False
        }

    def test_source(self, source: Source):
        raise NotImplementedError

    @timeout(max_check_time_seconds)
    def check_query(self, source: Source):
        info = self.test_source(source)

        if not info:
            return False

        estimated_cost = info["estimated_cost"]
        estimated_total = info["estimated_total"]
        retrieved_columns = info["retrieved_columns"]
        retrieved_column_names = info["retrieved_column_names"]
        retrieved_column_types = info.get("retrieved_column_types", {})
        exists_shape_id = info["exists_shape_id"]
        description = info["description"]

        self.info(
            "Query plan statistics",
            {
                "Estimated cost": f"{estimated_cost:0.3f}Gb",
                "Total cost:": f"{estimated_total:0.3f}Gb",
                "Retrieved fields": f"{len(retrieved_columns)}",
            },
        )
        fields_display = (
            {name: retrieved_column_types[name] for name in retrieved_column_names}
            if retrieved_column_types
            else retrieved_column_names
        )
        self.info("Query return fields", fields_display)
        self.info("Description", description)

        computed_columns = (
            {c.ref for c in comp}
            if (
                (trans := source.transform)
                and (data := trans.data)
                and (comp := data.compute)
            )
            else set()
        )
        
        if computed_columns:
            self.info("Computed columns", computed_columns)

        if isref(source.shape.id):
            if exists_shape_id:            
                self.info(
                    f"The field shape_id does exists as {source.shape.id.ref} in query fields.",
                )
            elif source.shape.id.ref in computed_columns:
                self.info(
                    f"The field shape_id is computed by {source.shape.id.ref} field.",
                )
            else:
                self.error(
                    f"The field shape_id does not exists as {source.shape.id.ref} in query fields.",
                )                
        else:
            self.info(
                f"The field shape.id is constant to {source.shape.id} in query fields."
            )

        if estimated_total > 1:
            raise QueryTooLarge()
        
        if column_not_found := {
            c.name
            for c in source.columns
            if c.name not in retrieved_column_names and c.eval is None
        } - computed_columns:
            raise QueryNotSolveAllColumns(list(column_not_found))

        if (
            refcolumn_not_found := set(
                self.column_refs(source, only_categorizables=True)
            )
            - set(retrieved_column_names)
            - computed_columns
        ):
            raise QueryNotSolveAllRefColumns(refcolumn_not_found)

        if override_columns := computed_columns.intersection(
            set(retrieved_column_names)
        ):
            raise QueryOverrideComputedColumns(override_columns)

        self.info(
            "Query structure OK",
            {"Columns validated": len(source.columns), "Query columns": len(retrieved_column_names)},
        )

        return exists_shape_id or source.shape.id.ref in computed_columns

    @timeout(max_check_time_seconds)
    def check_stats(self, source: Source):
        stats = self.stats(source)

        if not stats:
            return False

        total_rows = next((v for k, v in stats if k == "Row numbers"), None)
        if total_rows is not None:
            self.info(f"Query returned {total_rows} records")

        self.info(f"Stats", stats)
        return True

    @timeout(max_check_time_seconds)
    def check_warnings(self, source: Source):
        warnings = self.warnings(source)
        if warnings:
            self.warning(
                f"Relational issues",
                [f"{col}\n\n{desc}\n" for col, desc in warnings.items()],
            )
        return True

    @cache(
        "obs",
        lambda self, slug, shape_group, shape_period: f"{slug}-{shape_group}-{shape_period}",
    )
    def retrieve_observables(self, slug, shape_group, shape_period):
        start_time = time()
        try:
            # Fast path opcional (GIQMD_WH_CONN): leer los observables de la DB en vez de la
            # API paginada (que con 357k celdas tumba el servicio). Misma forma que la API.
            if os.environ.get("GIQMD_WH_CONN"):
                return self._retrieve_observables_db(shape_group, shape_period)
            return list(
                self.geoecon_api.get_observables_by_group(
                    name=shape_group, period=shape_period
                )
            )
        finally:
            query_time = time() - start_time
            self.info(
                f"Observable query {slug}:{shape_group}:{shape_period} time",
                [f"{query_time:0.3f}seg"],
            )

    def _retrieve_observables_db(self, shape_group, shape_period):
        import psycopg2

        conn = psycopg2.connect(os.environ["GIQMD_WH_CONN"])
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT o.group_id, o.group_parent_id, o.name, s.name, absc.name "
                "FROM wh.observables o "
                "JOIN wh.observable_groups g ON g.uuid = o.group_uuid "
                "JOIN wh.observable_scales s ON s.uuid = o.scale_uuid "
                "LEFT JOIN wh.observable_scales absc ON absc.uuid = s.abstract_scale_uuid "
                "JOIN wh.periods p ON p.uuid = o.period_uuid "
                "WHERE g.name = %s AND p.name = %s",
                (shape_group, str(shape_period)),
            )
            return [
                {
                    "group_id": r[0],
                    "group_parent_id": r[1],
                    "name": r[2],
                    "scale": {
                        "name": r[3],
                        "abstract_scale": ({"name": r[4]} if r[4] else None),
                    },
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    @memory_time_logger
    def get_observables(self, source: Source):
        # Multi-país: recuperar observables de TODOS los grupos iso3 auto-creados (no hay un único
        # `shape.group.name`). Named group → un solo grupo (comportamiento actual).
        if isref(source.shape.group):
            group_names = list(self.obs_groups.keys())
        else:
            group_names = [source.shape.group.name]
        raw_observables = [
            o
            for group_name in group_names
            for o in self.retrieve_observables(
                source.slug, group_name, source.shape.period.name
            )
        ]
        obs = pd.DataFrame(
            [
                (
                    str(o["group_id"]),
                    str(o["group_parent_id"]),
                    o["scale"]["name"],
                    abs["name"] if (abs := o["scale"]["abstract_scale"]) else None,
                    o["name"],
                )
                for o in raw_observables
            ],
            columns=[
                "group_id",
                "group_parent_id",
                GroupScaleEnum.CONCRETE_SCALE.value,
                GroupScaleEnum.ABSTRACT_SCALE.value,
                "name",
            ],
        ).astype(
            {
                "group_id": "category",
                "group_parent_id": "category",
                GroupScaleEnum.CONCRETE_SCALE.value: "category",
                GroupScaleEnum.ABSTRACT_SCALE.value: "category",
            }
        )

        incomplete_abstract_scales = obs["abstract_scale"].isna()
        if any(incomplete_abstract_scales):
            if not pd.api.types.is_categorical_dtype(obs["abstract_scale"]):
                obs["abstract_scale"] = obs["abstract_scale"].astype("category")

            new_categories = obs["concrete_scale"].dropna().unique()
            obs["abstract_scale"] = obs["abstract_scale"].cat.add_categories(
                new_categories
            )
            obs.loc[incomplete_abstract_scales, "abstract_scale"] = obs[
                incomplete_abstract_scales
            ]["concrete_scale"]

        if (select := source.select) and (sel_obs := select.observables):
            if to_ignore := sel_obs.ignore:
                if isinstance(to_ignore, list):
                    obs = obs[~obs["group_id"].isin(to_ignore)]
                elif isinstance(to_ignore, dict):
                    x = [obs[k.ref].isin(v) for k, v in to_ignore.items()]
                    obs = obs[~obs["group_id"].isin(to_ignore)]
            if scales := sel_obs.shape_scale:
                obs = obs[
                    obs[source.shape.group_scale.value]
                    .str.lower()
                    .isin([s.name.lower() for s in ObservableScale.expand(scales)])
                ]

        return obs.reset_index(drop=True)

    def do_source_validation(
        self, source: Source, observables: pd.DataFrame, data: pd.DataFrame
    ):
        if (validation := source.validation) and (obs_val := validation.observables):
            if ignored_src := obs_val.ignore:
                ignored = (
                    ignored_src if isinstance(ignored_src, list) else [ignored_src]
                )
                observables = observables[-(observables["group_id"].isin(ignored))]
            if shape_scales := set(s.lower() for s in obs_val.shape_scale):
                all_scales = set(observables["scale"].str.lower().unique())
                if shape_scales - all_scales:
                    raise ObservableScaleIssue(
                        f"Filtering by administrative level/s {shape_scales}",
                        f"But '{source.shape.group}' only support {all_scales} scales",
                    )
                selection = observables["scale"].isin(shape_scales)
                if not any(selection):
                    raise ObservableNotFound(
                        [
                            f"Filtering by administrative level/s {shape_scales}",
                            f"But '{source.shape.group}' only support {all_scales} scales",
                        ]
                    )
                self.observable_selection = selection
        return not self.has_duplicates(source, data)

    def do_source_selection(self, source: Source, df: pd.DataFrame):
        to_ignore = source.select and source.select.data and source.select.data.ignore
        # En read_source, "group_id" se renombra DESPUÉS de este paso
        # (df.rename({shape.id.ref: "group_id"}) / df.assign(group_id=...)).
        # Acá la columna todavía se llama como el ref de shape.id cuando es ref,
        # así que resolvemos el nombre real para no romper con KeyError: 'group_id'.
        group_col = (
            source.shape.id.ref
            if (source.shape and isref(source.shape.id))
            else "group_id"
        )
        if to_ignore and isinstance(to_ignore, list):
            df = df[~df[group_col].isin(to_ignore)]
        elif to_ignore and isinstance(to_ignore, dict):
            df = df[
                ~np.any(
                    [
                        df[column.ref].isin(values)
                        for column, values in to_ignore.items()
                    ],
                    axis=0,
                )
            ]
        return df

    def do_source_transformation(self, source: Source, data: pd.DataFrame):
        if isref(source.shape.id):
            group_id = source.shape.id.ref
        else:
            if 'group_id' in data.columns:
                data['group_id_old'] = data['group_id']
            group_id = 'group_id'
            data[group_id] = source.shape.id

        if transformation := source.transform and source.transform.shape:
            if diss := transformation.dissolve:
                data = (
                    data.dissolve(by=diss.by, aggfunc=diss.aggfunc)
                    if not isinstance(diss, bool)
                    else data.dissolve()
                )

        if transformation := source.transform and source.transform.data:
            try:
                data = data.assign(**transformation.do_compute(data))
            except Exception as err:
                raise ColumnEvaluationError(str(err))

            data = data.astype({group_id: str})
            data[group_id] = data[group_id].str.strip()

            for src, value in transformation.clone.items():
                new_line = data[data[group_id] == src]
                new_line.loc[:, group_id] = value
                data = pd.concat([data, new_line], ignore_index=True)
            for src, value in transformation.update.items():
                data.loc[data[group_id] == src, group_id] = value
            for target, maps in transformation.substitute.items():
                for old_str, new_str in maps.items():
                    dtype = data[target.ref].dtype
                    data[target.ref] = (
                        data[target.ref]
                        .astype("str")
                        .str.replace(old_str, new_str)
                        .astype(dtype)
                    )

            try:
                col_evals = {
                    col.name: eval(col.eval)
                    for col in source.columns
                    if col.eval is not None
                }
                data = data.assign(**col_evals)
            except Exception as err:
                raise ColumnEvaluationError(str(err))

        for c in source.columns:
            if c.input_encoding and (c.input_encoding != source.input_encoding):
                try:
                    data[c.name] = data[c.name].apply(
                        lambda r: r.encode(source.input_encoding.value).decode(
                            c.input_encoding.value
                        )
                    )
                except UnicodeDecodeError as err:
                    raise EncodingError(
                        f"Columns {c.name} with bad encoding {c.input_encoding}: {err}"
                    )

        encoding_error = [
            c
            for c in data.columns
            if data[c].dtype == object
            and not es_legible_unicode(", ".join(str(t) for t in data[c]))
        ]
        if encoding_error:
            raise EncodingError({"Columns with bad strings": encoding_error})

        try:
            return data[
                [group_id]
                + (pre_columns := [c.name for c in source.columns if c.eval is None])
                + [
                    c
                    for c in self.column_refs(source)
                    if (
                        (isref(source.shape.id) and c != source.shape.id.ref)
                        or (not isref(source.shape.id))
                    )
                    and c
                    and c not in pre_columns
                ]
            ]
        except KeyError as err:
            raise FieldNotFound(
                {"Message": f"-{err}-", "Current columns": list(data.columns)}
            )

    def has_duplicates(self, source: Source, data: pd.DataFrame):
        logging.info("Checking for duplicates")
        opening_refs = self.column_refs(source, only_categorizables=True)
        if any((count_group_id := data.value_counts(["group_id"] + opening_refs)) > 1):
            repeats = count_group_id[count_group_id > 1].reset_index()
            raise DuplicatedDataError(
                repeats.drop(
                    columns=(
                        [source.shape.geometry.ref]
                        if isref(source.shape.geometry)
                        else []
                    ),
                    errors="ignore",
                )
            )
        return False

    def fill_defaults(self, source, data, observables, opennings):
        defaults = source.get_defaults()
        full_comb = pd.merge(
            pd.Series(observables["group_id"].unique().astype(str), name="group_id"),
            opennings,
            how="cross",
        ).assign(**{n: v for n, v in defaults.items()})
        data = data.merge(
            full_comb,
            on=["group_id"] + list(set(opennings.columns) - {"index"}),
            how="right",
            suffixes=("_A", "_B"),
        )
        for n in defaults.keys():
            data[n + "_A"] = data[n + "_A"].fillna(data[n + "_B"])
        data = data.drop(columns=[c.name + "_B" for c in source.columns] + ["index"])
        return data.rename(columns={c.name + "_A": c.name for c in source.columns})

    @timeout(max_agg_time_seconds)
    @cache(
        "do_source_autoaggregation",
        lambda self, source, *args: f"{source.slug}",
    )
    @memory_time_logger
    def do_source_autoaggregation(
        self, source: Source, observables: pd.DataFrame, data: pd.DataFrame
    ):
        logging.info("Aggregating")
        opening_refs = self.column_refs(source, only_categorizables=True)
        data = data.set_index("group_id")
        opennings = (
            data[opening_refs]
            .reset_index()
            .drop(columns=["group_id"])
            .dropna(how="all")
            .drop_duplicates()
            .reset_index()
        )
        data_columns = [
            c.name
            for c in source.columns
            if c.eval is None
            and c.unit in MEASUREMENTUNIT_AGG_MAP
            and MEASUREMENTUNIT_AGG_MAP[c.unit]
        ]

        if not data_columns:
            self.info("No columns to aggregate")
            return self.fill_defaults(source, data, observables, opennings)

        self.info(
            "Agregation of columns",
            {c.name: MEASUREMENTUNIT_AGG_MAP[c.unit] for c in source.columns},
        )

        logging.info("Computing opening: %s", ",".join(opennings.columns))

        result = (
            pd.concat(
                (
                    self.proc_openning(
                        source, observables, data, opening_refs, openning, data_columns
                    )
                    for row, openning in opennings.iterrows()
                ),
                ignore_index=True,
            )
            if not opennings.empty
            else self.do_source_autoggregation_fix_oppening(
                source, observables, data[data_columns]
            )
        )

        return result.assign(
            **{
                e.name: eval(e.eval, dict(result))
                for e in source.columns
                if e.eval is not None
            }
        )

    def proc_openning(
        self,
        source: Source,
        observables: pd.DataFrame,
        data: pd.DataFrame,
        opening_refs: list[str],
        openning: pd.Series,
        data_columns: list[str],
    ):
        logging.info("%s", ",".join(f"{v}" for v in openning.values))
        data_filter = (data[opening_refs] == openning[opening_refs]).all(axis=1)
        agg_data = self.do_source_autoggregation_fix_oppening(
            source, observables, data[data_columns][data_filter]
        )
        if agg_data is None:
            return None  # TODO: Debería ser un raise de excepción

        left = agg_data.reset_index()
        right = pd.DataFrame(openning[opening_refs]).transpose()
        left["__m__"] = 0
        right["__m__"] = 0
        return pd.merge(left, right, left_on="__m__", right_on="__m__").drop(
            columns=["__m__"]
        )

    @memory_time_logger
    def do_source_autoggregation_fix_oppening(
        self,
        source: Source,
        observables: pd.DataFrame,
        data: pd.DataFrame,
        x=0,
    ):
        if not (
            column_agg := {
                c.name: MEASUREMENTUNIT_AGG_MAP[c.unit]
                for c in source.columns
                if c.eval is None and c.unit != MeasurementUnit.INDICE
            }
        ):
            logging.info("No columns to aggregate.")
            return data

        logging.debug("Merging data with observables [%i]", x)
        data_obs = data.merge(
            observables,
            on="group_id",
            indicator=True,
            how="outer",
        )
        defaults = source.get_defaults()

        logging.debug("Checking completitud")
        if any(selection := data_obs["_merge"] == "left_only"):
            raise ObservationWithoutObservable(data_obs[selection])

        if all(data_obs["_merge"] == "both"):
            logging.debug("Aggregation ready")
            return data_obs.set_index("group_id")[data.columns]

        if (set(data_obs["group_parent_id"]) - set(data_obs["group_id"])) in (
            {},
            {"None"},
        ):
            logging.debug("Aggregation ready. Set defaults.")
            for col_name, default_value in defaults.items():
                data_obs.loc[data_obs["_merge"] == "right_only", col_name] = (
                    default_value
                )
            return data_obs.set_index("group_id")[data.columns]

        logging.debug("Solving leaf data")
        parents = data_obs["group_parent_id"].unique()
        without_data = data_obs["_merge"] == "right_only"
        without_childs = ~data_obs["group_id"].isin(parents)

        if not (
            obs_issue := data_obs[without_childs & without_data]["group_id"].isin(
                parents
            )
        ).empty:
            if (
                (trans := source.transform)
                and (trans_on := trans.on)
                and (
                    trans_on.observable_without_observation
                    == ObservableWithoutObservationActions.USE_DEFAULTS
                )
                and (defaults := source.get_defaults())
            ):
                if (
                    without_default := set(data_obs.columns)
                    - defaults.keys()
                    - {
                        "group_parent_id",
                        "_merge",
                        "name",
                        "scale",
                        "group_id",
                        "abstract_scale",
                        "concrete_scale",
                    }
                ):
                    raise ColumnWithoutDefault(
                        "Columns without defaults: %s", without_default
                    )
                data_obs.loc[obs_issue.index, ["_merge"] + list(defaults.keys())] = [
                    "both"
                ] + list(defaults.values())
            else:
                raise ObservableWithoutObservation(data_obs.loc[obs_issue.index])

        leaf_data = data_obs.loc[without_data & without_childs, data.columns].fillna(
            value={
                c.name: eval(f"{MEASUREMENTUNIT_AGG_MAP[c.unit]}([])")
                for c in source.columns
            }
        )
        data_obs = data_obs.combine_first(leaf_data)
        data_obs.loc[without_data & without_childs, "_merge"] = "both"

        if all(data_obs["_merge"] == "both"):
            logging.debug("Aggregation ready")
            return data_obs.set_index("group_id")[data.columns]

        logging.debug("Grouping")
        group_parent_id_grp = data_obs[~data_obs["group_parent_id"].isnull()].groupby(
            "group_parent_id", observed=True
        )

        computed = (
            group_parent_id_grp.filter(lambda p: any(p["_merge"] == "both"))
            .groupby("group_parent_id", observed=True)
            .agg(column_agg)
            .rename_axis("group_id")
        )

        if computed.empty:
            return data

        selection = data_obs["group_id"].isin(set(computed.index)) | ~without_data
        data_to_aggregate = (
            data_obs[selection]
            .set_index("group_id")
            .combine_first(computed)[data.columns]
        )

        return self.do_source_autoggregation_fix_oppening(
            source, observables, data_to_aggregate, x + 1
        )

    @timeout(max_check_time_seconds)
    @memory_time_logger
    def check_observables(self, source: Source):

        try:
            observables = self.get_observables(source)
        except ObservableNotFound:
            raise NoObservables(
                f"Observables with group {source.shape.group} are not available on WH"
            )

        data = self.read_source(source)

        if not pd.api.types.is_string_dtype(data["group_id"]):
            self.warning("data group_id is not string", data["group_id"][0:10])

        group_id_cat = pd.CategoricalDtype(
            sorted(
                set(data["group_id"].astype(str)).union(
                    set(observables["group_id"].dtype.categories)
                )
            )
        )
        data = data.astype({"group_id": group_id_cat})

        if self.has_duplicates(source, data):
            return False

        observables = observables.astype(
            {"group_id": group_id_cat, "group_parent_id": group_id_cat}
        )

        # mini-prueba: cobertura del shape.id contra las geometrías existentes.
        # Si NINGÚN group_id de la data matchea una geometría, el merge outer caería
        # silenciosamente al path de autoagregación y el check pasaría "Ok" con 0 datos
        # cargables. Lo convertimos en un error claro (caso típico: gid con espacios/
        # padding por to_char(.,'00000') en lugar de 'FM00000').
        data_ids = set(data["group_id"].astype(str))
        obs_ids = set(observables["group_id"].astype(str))
        if data_ids and not (data_ids & obs_ids):
            raw_ids = data["group_id"].astype(str)
            has_ws = bool((raw_ids != raw_ids.str.strip()).any())
            hint = (
                " Hay valores con espacios al inicio/fin — revisar el formato del "
                "shape.id (ej. to_char(col,'FM00000') en vez de '00000')."
                if has_ws
                else ""
            )
            self.error(
                "Ningún group_id (shape.id) de la data matchea geometrías existentes",
                [
                    f"{len(data_ids)} group_id en la data, 0 matchean geometrías del "
                    f"grupo '{source.shape.group.name}'.{hint}",
                    f"muestra data: {sorted(data_ids)[:5]}",
                    f"muestra geometrías: {sorted(obs_ids)[:5]}",
                ],
            )
            return False

        if not all(
            data[["group_id"]].merge(
                observables[["group_id"]], on="group_id", how="outer", indicator=True
            )["_merge"]
            == "both"
        ):
            self.info(
                "More observables than data, I guess we need aggregate to solve all observables."
            )
            data = self.do_source_autoaggregation(source, observables, data)
            if data is None:
                return False
            data = data.reset_index()

        if (
            data is None
            or data.empty
            or not self.do_source_validation(source, observables, data)
        ):
            return False

        data_obs = data.astype({"group_id": observables["group_id"].dtype}).merge(
            observables, on="group_id"
        )
        obs_scale_count = observables.value_counts(["abstract_scale"])
        data_scales_count = data_obs.value_counts(
            ["abstract_scale", "group_id"]
            + self.column_refs(source, only_categorizables=True)
        )

        grp_obs_set = set(observables["group_id"])
        dta_obs_set = set(data["group_id"].astype("str").str.strip())

        observables_not_in_data = grp_obs_set - dta_obs_set
        observables_not_in_grp = dta_obs_set - grp_obs_set
        data_without_obs = data[data["group_id"].isin(list(observables_not_in_grp))]
        obs_without_data = observables[
            observables["group_id"].isin(observables_not_in_data)
        ]

        self.info("Observable resume in group", obs_scale_count)
        self.info("Observable resume in data", data_scales_count)

        if not obs_without_data.empty:
            raise ObservableWithoutObservation(obs_without_data)

        if not data_without_obs.empty:
            raise ObservationWithoutObservable(data_without_obs)

        return True

    @memory_time_logger
    def check_geometry(self, source):
        in_data = self.read_source(source)
        geometry = self.get_geometry(source, in_data)
        geodata = gpd.GeoDataFrame(
            in_data.drop(
                columns=(
                    [source.shape.geometry.ref] if isref(source.shape.geometry) else []
                ),
                errors="ignore",
            ),
            geometry=geometry,
        )
        if geodata.crs is None:
            self.warning("No CRS defined — assuming EPSG:4326 (WGS84 lat/lon)")
            geodata = geodata.set_crs(epsg=4326)
        else:
            self.info("Sistema de referencia de coordenadas (CRS)", geodata.crs.to_string())

        try:
            geodata = geodata.to_crs(epsg=4326)
        except Exception as err:
            self.error("Error on geometry", [str(err)])
            return False
        return True

    @memory_time_logger
    def check_time(self, source):
        column_cnt = len(source.columns)
        openning_columns = self.group_by_cols(source)
        data = self.read_source(source)

        if source.shape.geometry is None:
            data_obs = data.merge(self.get_observables(source), on="group_id")
        else:
            data_obs = data
            if "scale" not in data_obs.columns:
                data_obs["scale"] = source.shape.scale.name
            if "abstract_scale" not in data_obs.columns:
                data_obs["abstract_scale"] = (
                    source.shape.scale.abstract_scale.name
                    if source.shape.scale.abstract_scale
                    else source.shape.scale.name
                )

        openning_items = {
            col: list(data_obs[col].unique())
            for col in openning_columns
            if col != "abstract_scale"
        }

        if openning_items:
            self.info("Openning items by columns", openning_items)
        else:
            self.info("No openning items")

        openning_cnt = {
            col: len(data_obs[col].unique())
            for col in openning_columns
            if col != "abstract_scale"
        }
        total_obs_scales_cnt = len(data_obs["abstract_scale"].unique())
        declared_scales_cnt = len(source.select.observables.shape_scale)
        scales_cnt = max(total_obs_scales_cnt, declared_scales_cnt)

        instances_count = (
            column_cnt
            * scales_cnt
            * (reduce(lambda a, b: a * b, openning_cnt.values()) if openning_cnt else 1)
        )

        geometry_count = len(data_obs.index) if source.shape.geometry else 0

        self.info(
            "Max items to upload",
            {"Instances": instances_count, "Geometries": geometry_count},
        )

        geometry_time = 17
        instance_time = 25
        total_instance_time = instances_count * instance_time
        total_geometry_time = geometry_count * geometry_time

        self.info(
            "Source statistics",
            {
                "Columns": column_cnt,
                "# adm levels": scales_cnt,
                **{
                    f"openning {i}: {k}": v
                    for i, (k, v) in enumerate(openning_cnt.items())
                    if k != "abstract_scale"
                },
            },
        )

        self.info(
            "Geometry uploading time",
            {
                "seconds": total_geometry_time,
                "minutes": total_geometry_time / 60,
                "hours": total_geometry_time / (60 * 60),
                "days": total_geometry_time / (60 * 60 * 24),
            },
        )

        self.info(
            "Instance uploading time",
            {
                "seconds": total_instance_time,
                "minutes": total_instance_time / 60,
                "hours": total_instance_time / (60 * 60),
                "days": total_instance_time / (60 * 60 * 24),
            },
        )

        return True

    def check_scales(self, source: Source):
        # Mini-prueba: las escalas declaradas (shape_scale) deben resolver a un uuid
        # en el warehouse. Si alguna no resuelve (p.ej. abstractas group-less que no
        # matchean group=arg), el deploy crashea al crear instancias (scale_uuid None);
        # lo adelantamos a un error de check claro para que el problema se vea acá y
        # el deploy no se habilite hasta resolverlo.
        if self.context is None:
            return True  # sin anclas de data no podemos resolver escalas; no bloquear
        if isref(source.shape.group):
            # Multi-país: las escalas "País" concretas se auto-crean por país en el deploy
            # (solve_obs_groups), no existen aún en el warehouse → no pre-resolver acá. La escala
            # declarada (abstracta "Nivel Administrativo 0") ya la valida check contra data/.
            return True
        try:
            scales = self.solve_obs_scales(source, self.read_source(source))
        except Exception as exc:
            self.error("No se pudieron resolver las escalas declaradas", [str(exc)])
            return False
        unresolved = sorted(name for name, sc in (scales or {}).items() if sc is None)
        if unresolved:
            self.error(
                "Escalas declaradas que no resuelven en el warehouse",
                [
                    f"No resuelven para el grupo '{source.shape.group.name}': {unresolved}.",
                    "El deploy fallaría al crear instancias (scale_uuid None). Revisar el "
                    "registro de esas escalas en el warehouse o el shape_scale del YAML.",
                ],
            )
            return False
        return True

    def check(
        self,
        source: Source,
        environment: Environments = Environments.PROD,
        context: dict | None = None,
    ):
        self.setup(environment=environment, context=context)
        try:
            (
                self.check_query(source)
                and self.check_stats(source)
                and self.check_warnings(source)
                and (
                    self.check_observables(source)
                    if source.shape.geometry is None
                    else self.check_geometry(source)
                )
                and self.check_scales(source)
                and self.check_time(source)
            )
        except ProcessorError as exc:
            logging.error(exc)
            self.message(**exc.report())
        except TimeoutException as exc:
            logging.error(exc)
            self.message(exc.typo, exc.message, [f"Waiting time: {exc.time}s"])
        except RecursionError as exc:
            logging.error(exc)
            self.error(str(exc), [f"Recursion error on: {source.slug}s"])

        return self.reset()

    @cache(
        "solve_source",
        lambda self, source: f"{source.slug}",
    )
    def solve_source(self, source: Source):
        resp = self.geoecon_api.get_source(source)
        if resp is None:
            resp = self.geoecon_api.new_source(source)
        return resp

    def solve_class(self, name: str, typo: str, description: str):
        existing_class = self.geoecon_api.get_class(name, typo)
        if not existing_class:
            return self.geoecon_api.new_class(name, typo, description)
        return existing_class

    @cache(
        "solve_periods",
        lambda self, source, *args: f"{source.slug}",
    )
    def solve_periods(self, source: Source, df: pd.DataFrame):
        periods = (
            (
                Period(**self.geoecon_api.get_period(p)).get(self.geoecon_api)
                if isinstance(p, str)
                else p.get(self.geoecon_api)
            )
            for p in set(source.periods(df))
        )
        return {getattr(p, "name", p): p.get(self.geoecon_api) for p in periods}

    def solve_classes(self, source: Source):
        return {col.name: self.solve_class(col) for col in source.columns}

    @cache(
        "solve_attributes",
        lambda self, source, *args: f"{source.slug}",
    )
    def solve_attributes(self, source: Source, df: pd.DataFrame):
        # TODO: En el caso que name apunte a una columna del dataframe
        return {
            column.name: self.solve_attribute(
                column.name,
                column.unit,
                column.description,
                None,
            )
            for column in source.columns
        }

    def solve_attribute(self, name, unit, description, parent_uuid):
        existing_attribute = self.geoecon_api.get_attribute(name)
        if not existing_attribute:
            return self.geoecon_api.new_attribute(name, unit, description, parent_uuid)
        return existing_attribute

    @cache(
        "solve_topics",
        lambda self, source: f"{source.slug}",
    )
    def solve_topics(self, source: Source):
        notopic_topic = {
            "code": "notopic",
            "help": "No topic",
            "order": 1,
            "name": "No topic",
            "icon": "notopic.png",
            "description": "No topic",
        }
        return {
            topic: self.geoecon_api.get_topic(topic or "notopic")
            or self.geoecon_api.new_topic(**notopic_topic)
            for topic in set(c.topic for c in source.columns)
        }

    @cache(
        "solve_indicators",
        lambda self, source, *args: f"{source.slug}",
    )
    def solve_indicators(self, source: Source, data: pd.DataFrame):
        return {
            f"{col.name}:{indicator['code']}": self.geoecon_api.get_indicator(
                indicator["code"]
            )
            or self.geoecon_api.new_indicator(
                description=col.description, attribute=col.name, **indicator
            )
            for col in source.columns
            for indicator in col.get_indicators(data)
        }

    def solve_indicator(self, name, code, description, attribute):
        return self.geoecon_api.get_indicator(code) or self.geoecon_api.new_indicator(
            name, code, description, attribute
        )

    def solve_obs_class(self, name: str):
        resp = self.geoecon_api.get_obs_class(name)
        if resp is None:
            resp = self.geoecon_api.new_obs_class(name)
        return resp

    def solve_obs_group(self, obsgrp: ObservableGroup):
        for s in obsgrp.scales:
            self.solve_obs_scale(s, obsgrp)

        return self.geoecon_api.get_obs_group(
            obsgrp.name
        ) or self.geoecon_api.new_obs_group(
            obsgrp.name, obsgrp.typo, obsgrp.description
        )

    @cache(
        "solve_obs_groups",
        lambda self, source, *args: f"{source.slug}",
    )
    def solve_obs_groups(self, source: Source, df: pd.DataFrame):
        # Multi-país: `shape.group` es un ColumnRef (iso3-lower por feature) → auto-crear grupo +
        # escala País por valor único. Named group → comportamiento actual intacto (.get()).
        if isref(source.shape.group):
            return self._solve_obs_groups_by_column(source, df)
        return {
            obs_group.name: obs_group.get(self.geoecon_api)
            for obs_group in source.get_obs_groups(df)
        }

    def _iso3_country_names(self, source: Source, df: pd.DataFrame) -> dict:
        group_col = source.shape.group.ref
        name_col = source.shape.name.ref if isref(source.shape.name) else None
        if not name_col:
            return {}
        return (
            df[[group_col, name_col]]
            .astype(str)
            .drop_duplicates()
            .assign(_k=lambda d: d[group_col].str.strip().str.lower())
            .set_index("_k")[name_col]
            .to_dict()
        )

    def _abstract_scale0(self):
        abstract0 = next(
            (
                s
                for s in (self.context or [])
                if isinstance(s, ObservableScale) and s.name == "Nivel Administrativo 0"
            ),
            None,
        )
        if abstract0 is None:
            raise NoObservations(
                "No se encontró la escala abstracta 'Nivel Administrativo 0' en data/ (00_scales.yaml)"
            )
        return abstract0

    def _solve_obs_groups_by_column(self, source: Source, df: pd.DataFrame):
        """`shape.group: !ColumnRef` (adm0 multi-país). Por cada valor único de la columna
        (iso3-lower) auto-crea (idempotente por name) un ObservableGroup ``type=country`` —
        EXACTAMENTE como los ``<iso3>_geoecon_obs.yml`` single-country de América (paridad total:
        los 27 grupos ya existentes se reusan por get-or-create, no se duplican). La escala "País"
        concreta se crea aparte en ``_solve_pais_scales_by_column`` (NO por side-effect, para que
        el @cache de solve_obs_groups no la pierda). Devuelve {iso3-lower: ObservableGroup}."""
        names = self._iso3_country_names(source, df)
        resolved = {}
        for iso3 in source.get_obs_groups(df):
            key = str(iso3).strip().lower()
            country_name = names.get(key, key)
            grp = ObservableGroup(
                name=key,
                typo="country",
                description=f"Grupo geográfico correspondiente a {country_name} (adm0 mundial).",
                scales=[],
            )
            resolved[key] = grp.create(self.geoecon_api)  # get-or-create (idempotente)
        return resolved

    def _solve_pais_scales_by_column(self, source: Source, df: pd.DataFrame):
        """Escala concreta **País** (bajo la abstracta "Nivel Administrativo 0") por país iso3,
        group-scoped al grupo ya resuelto en ``self.obs_groups``. NO cacheada (se llama una vez en
        build_observables) → no depende de side-effects perdibles por @cache. Devuelve
        {iso3-lower: ObservableScale(País) con uuid}. Idempotente (get-or-create; reusa las 27 de
        América). Este método es el que hace pasar wh.observable_scales name='País' de 27 → ~240."""
        abstract0 = self._abstract_scale0()
        names = self._iso3_country_names(source, df)
        pais_scales = {}
        for iso3 in source.get_obs_groups(df):
            key = str(iso3).strip().lower()
            group = self.obs_groups[key]
            country_name = names.get(key, key)
            pais_scale = ObservableScale(
                name="País",
                description=f"{country_name} (país / Nivel Administrativo 0).",
                group=group,
                abstract_scale=abstract0,
                typo=ObservableScaleTypeEnum.UTA,
            )
            pais_scales[key] = pais_scale.create(self.geoecon_api)
        return pais_scales

    def solve_obs_scale(
        self, scale: ObservableScale, group: ObservableGroup | None = None
    ):
        resp = scale.get(self.geoecon_api)
        if resp is None:
            resp = scale.create()
        return resp

    @cache(
        "solve_obs_scales",
        lambda self, source, *args: f"{source.slug}",
    )
    def solve_obs_scales(self, source: Source, df: pd.DataFrame):
        def get_name(s):
            if isinstance(s, str):
                return s
            if isinstance(s, ObservableScale):
                return s.name
            if isinstance(s, tuple):
                return s[0]
            raise ValueError("No valid scale type")

        def get_scale(s, group=None):
            scales = (
                scale
                for g in self.context
                if isinstance(g, ObservableGroup)
                if g.name == source.shape.group.name
                for scale in g.scales
            )

            if isinstance(s, ObservableScale):
                # Las escalas abstractas (typo:abstract, sin abstract_scale propia)
                # viven group-less en el warehouse. Forzarles el grupo rompe el
                # lookup (.get filtra por group_uuid=<grupo> y no matchea el registro
                # group-less) → devuelve None → el deploy crashea al crear instancias.
                # Las instancias deployadas referencian la escala abstracta group-less
                # (ese es el modelo), así que la resolvemos sin grupo; solo las
                # concretas (con abstract_scale) llevan set_group.
                if s.abstract_scale is None:
                    return s
                return s.set_group(group)
            if isinstance(s, tuple):
                scale, absscale = s
                return next(
                    (
                        s.set_group(group)
                        for s in scales
                        if (
                            (scale.lower() in [n.lower() for n in s.aliases + [s.name]])
                            and (s.abstract_scale.name.lower() == absscale.lower())
                        )
                    ),
                    None,
                )
            if isinstance(s, str):
                scale_name = s
                return next(
                    (
                        scale.set_group(group)
                        for scale in scales
                        if scale.name == scale_name or scale_name in scale.aliases
                    ),
                    None,
                )

        resolved = {}
        for s in source.scales(df):
            solv_scale = get_scale(s, source.shape.group)
            if solv_scale is None:
                continue
            resolved[get_name(s).lower()] = solv_scale.get(self.geoecon_api)
            # Las instancias referencian la escala ABSTRACTA (group_scale = ABSTRACT_SCALE por
            # defecto; deploy_instance hace self.scales[group_data["abstract_scale"]]). En el
            # caso single-resolución (p.ej. h3 res-8) solo se yield-ea la escala concreta, así
            # que la abstracta no quedaría como key → registrarla también, resuelta group-less.
            abss = getattr(solv_scale, "abstract_scale", None)
            if abss is not None and abss.name.lower() not in resolved:
                abss_solv = get_scale(abss, source.shape.group)
                if abss_solv is not None:
                    resolved[abss.name.lower()] = abss_solv.get(self.geoecon_api)
        return resolved

    def delete_data_instance(
        self,
        uuid=None,
        name=None,
        code=None,
        indicator_uuid=None,
        class_uuid=None,
        data_period_uuid=None,
        group_uuid=None,
        period_uuid=None,
        scale_uuid=None,
    ):
        logging.info(
            f"Cleaning instances with: uuid={uuid},name={name},code={code},"
            f"indicator_uuid={indicator_uuid},class_uuid={class_uuid},"
            f"data_period_uuid={data_period_uuid},group_uuid={group_uuid},"
            f"period_uuid={period_uuid},scale_uuid={scale_uuid}"
        )
        for inst in self.geoecon_api.get_instances(
            uuid=uuid,
            name=name,
            code=code,
            indicator_uuid=indicator_uuid,
            class_uuid=class_uuid,
            data_period_uuid=data_period_uuid,
            group_uuid=group_uuid,
            period_uuid=period_uuid,
            scale_uuid=scale_uuid,
        ):
            self.geoecon_api.del_data_instances(inst["uuid"])

    def deploy_instance(
        self,
        source: Source,
        column: Column,
        data_instance: pd.DataFrame,
        group_data: dict,
    ):
        scale = group_data["abstract_scale"]
        # Multi-país: el grupo de ESTE layer sale de la columna-grupo (iso3) del group_data, no de
        # un único `shape.group.name`. Named group → el nombre fijo del grupo (comportamiento actual).
        if isref(source.shape.group):
            shape_group_key = str(group_data[source.shape.group.ref]).strip().lower()
        else:
            shape_group_key = source.shape.group.name
        period = unref(column.period, group_data)
        period = getattr(period, "name", period)
        class_name = column.class_name(group_data)
        class_type = column.class_type()
        class_description = column.description

        indicators = list(column.get_indicators(data_instance))
        assert len(indicators) == 1, "Unique indicator por layer"
        indicator_name = indicators[0]["name"]
        indicator_code = indicators[0]["code"]
        indicator_description = column.description
        indicator_attribute = column.name

        class_dict = self.solve_class(class_name, class_type, class_description)
        assert class_dict, "Class is required"
        indicator_dict = self.solve_indicator(
            indicator_name, indicator_code, indicator_description, indicator_attribute
        )
        assert indicator_dict, "Indicator is required"

        instance_name = "/".join(
            [source.slug, indicator_name]
            + sorted(str(i) for i in group_data.values())
            + ([period] if not isref(column.period) else [])
        )
        instance_code = slugify(instance_name)

        self.delete_data_instance(
            indicator_uuid=indicator_dict["uuid"],
            class_uuid=class_dict["uuid"],
            data_period_uuid=self.periods[period].uuid,
            group_uuid=self.obs_groups[shape_group_key].uuid,
            period_uuid=self.periods[unref(source.shape.period.name, group_data)].uuid,
            scale_uuid=self.scales[scale.lower()].uuid,
        )

        instance = self.geoecon_api.get_instance_by_code(
            instance_code
        ) or self.geoecon_api.new_instance(
            instance_name,
            instance_code,
            indicator_code,
            scale,
            class_name,
            class_type,
            source.shape.period.name,
            period,
            shape_group_key,
            source.slug,
        )

        self.info("Deployed instance", [instance, data_instance.describe()])
        logging.info(f"Uploading data instance {instance_name}({instance['uuid']}).")

        try:
            storage_report = self.geoecon_api.update_instance(
                instance["uuid"], data_instance[["group_id", "value"]]
            )
        except DataError as err:
            self.error("Deploy error", str(err))
        else:
            if not storage_report:
                self.warning("No storage report")
                return
            self.info("Deploy results", storage_report)
            input_data = storage_report["input"]
            stored_data = storage_report["stored"]
            if not compare_dicts(input_data, stored_data):
                self.error("Deploy results are not equal")

    def group_by_cols(self, source: Source):
        cols = set(self.column_refs(source, only_categorizables=True))
        shape = source.shape
        try:
            if isref(shape.scale):
                cols.remove(shape.scale.ref)
            if isref(shape.abstract_scale):
                cols.remove(shape.abstract_scale.ref)
        except ValueError:
            self.warning(
                "Expected columns on column refs are not in column_refs function.",
                {
                    "expected": [
                        shape.scale.ref if isref(shape.scale) else None,
                        shape.abstract_scale if isref(shape.abstract_scale) else None,
                    ],
                    "on_column_Refs": cols,
                },
            )

        # Multi-país: las instancias deben ser POR PAÍS → agrupar también por la columna-grupo
        # (iso3) para que cada layer resuelva su propio grupo en deploy_instance.
        if isref(source.shape.group):
            cols.add(source.shape.group.ref)

        if cols:
            return list(cols | {"abstract_scale"})
        else:
            return [source.shape.group_scale.value]

    def get_geometry(self, source: Source, in_data: pd.DataFrame):
        geometry = in_data[geo.ref] if isref(geo := source.shape.geometry) else geo
        if isinstance(geometry, str):
            geometry = wkt.loads(geometry)
        elif isinstance(geometry, Point):
            geometry = wkt.loads(geometry.to_geometry(in_data))
        elif not isinstance(geometry.dtype, gpd.array.GeometryDtype):
            try:
                geometry = wkt.loads(geometry)
            except:
                raise UnsupportedGeometryType(type(geometry))
        return geometry

    def build_observables(self, source: Source, in_data: pd.DataFrame):
        self.obs_class = {
            source.shape.obs_class.name.lower(): ObservableClass(
                **self.solve_obs_class(source.shape.obs_class.name)
            )
        }
        self.info("Shape observable class", self.obs_class)
        if self.obs_class is None or not self.obs_class:
            raise NoObservations("Cant deploy null observable group")

        geometry = self.get_geometry(source, in_data)
        # Multi-país: cada país usa su escala "País" CONCRETA (group-scoped), resuelta por el
        # valor de la columna-grupo (iso3) → paridad con América. Named group → resolución normal.
        if isref(source.shape.group):
            # Escala "País" concreta por país (group-scoped) → paridad con América. Se resuelve por
            # RETORNO (no side-effect) para no perderla si el @cache de solve_obs_groups saltea el cuerpo.
            # .astype(str) evita que pandas mapee sobre las CATEGORÍAS del dtype categorical (todas)
            # en vez de sobre los valores de las filas presentes.
            pais_scales = self._solve_pais_scales_by_column(source, in_data)
            scale_uuid = in_data[source.shape.group.ref].astype(str).map(
                lambda iso3: str(pais_scales[iso3.strip().lower()].uuid)
            )
            # group_uuid per-país: resolve_uuids (compartido) sólo mapea DataFrame, no Series —
            # lo resolvemos acá por país (mismo patrón que scale_uuid) sin tocar código compartido.
            group_uuid = in_data[source.shape.group.ref].astype(str).map(
                lambda iso3: str(self.obs_groups[iso3.strip().lower()].uuid)
            )
        else:
            scale_uuid = resolve_unrefs_uuid(source.shape.scale, in_data, self.scales)
            group_uuid = resolve_unrefs_uuid(source.shape.group, in_data, self.obs_groups)
        geodata = gpd.GeoDataFrame(
            {
                "group_id": in_data["group_id"],
                "reliability": source.reliability.value,
                "class_uuid": resolve_unrefs_uuid(
                    source.shape.obs_class, in_data, self.obs_class
                ),
                "scale_uuid": scale_uuid,
                "period_uuid": resolve_unrefs_uuid(
                    source.shape.period, in_data, self.periods
                ),
                "group_uuid": group_uuid,
                "source_uuid": self.source_inst["uuid"],
                "group_parent_id": unref(source.shape.parent_id, in_data),
                "name": (name := unref(source.shape.name, in_data)),
                "description": (unref(source.shape.description, in_data) or name),
                "geometry": geometry,
            },
            geometry="geometry",
        )

        self.upload_geodata(
            source,
            geodata,
            update_geometry=source.processing.update_geometry,
        )

        return self.get_observables(source)

    @on_exception
    def deploy(
        self,
        source: Source,
        environment: Environments,
        context: dict | None = None,
    ):
        """Deploya los layers asociados a un Source en un ambiente de GeoEcon.

        Args:
            source (Source): Fuente de origen de los datos.
            environment (Environments): Ambiente donde se deploya el Source

        Raises:
            NoObservables: No encuentra observables para deployar
            NoObservations: No encuentra datos para deployar
            ObservationWithoutObservable: Hay observacions para observables que no estan en WH
            ObservableWithoutObservation: Hay observables que no tienen datos en el Sources
        """
        self.setup(environment=environment, context=context)

        data = self.read_source(source)
        self.info("Data", data.describe())
        if data is None or data.empty:
            raise NoObservations("Cant deploy null observations")

        self.source_inst = self.solve_source(source)
        self.info("Source", self.source_inst)
        if self.source_inst is None or not self.source_inst:
            raise NoObservations("Cant deploy null sources")

        self.periods = self.solve_periods(source, data)
        self.info("Periods", self.periods)
        if self.periods is None or not self.periods:
            raise NoObservations("Cant deploy null periods")

        self.obs_groups = self.solve_obs_groups(source, data)
        self.info("Shape groups", self.obs_groups)
        if self.obs_groups is None or not self.obs_groups:
            raise NoObservations("Cant deploy null shape group")

        self.scales = self.solve_obs_scales(source, data)
        self.info("Scales", self.scales)
        if self.scales is None or not self.scales:
            raise NoObservations("Cant deploy null scales")

        attributes = self.solve_attributes(source, data)
        self.info("Attributes", attributes)
        if attributes is None or not attributes:
            raise NoObservations("Cant deploy null attributes")

        topics = self.solve_topics(source)
        self.info("Topics", topics)
        if topics is None or not topics:
            raise NoObservations("Cant deploy null topics")

        indicators = self.solve_indicators(source, data)
        self.info("Indicators", indicators)
        if indicators is None or not indicators:
            raise NoObservations("Cant deploy null indicator")

        if source.shape.geometry is None:
            observables = self.get_observables(source)
        else:
            observables = self.build_observables(source, data)

        if source.select and source.select.observables and source.select.observables.filtre:
            filtrable = observables.merge(data, on="group_id")[
                ["group_id", *(k.ref for k in source.select.observables.filtre.keys())]
            ]
            filtre = reduce(
                lambda a, b: a & b,
                (
                    filtrable[column.ref] == value
                    for column, value in source.select.observables.filtre.items()
                ),
            )
            observables = observables[
                observables.group_id.isin(filtrable[filtre].group_id)
            ].reset_index()

        self.info("Observables", observables)
        if observables is None or observables.empty:
            raise NoObservables("Cant deploy null observables")

        if not all(
            data[["group_id"]].merge(
                observables[["group_id"]], on="group_id", how="outer", indicator=True
            )["_merge"]
            == "both"
        ):
            self.info(
                "More observables than data, I guess we need aggregate to solve all observables."
            )
            data = self.do_source_autoaggregation(source, observables, data)
            if data is None:
                return False
            data = data.reset_index()

        data = data.assign(
            **{
                e.name: eval(e.eval, dict(data))
                for e in source.columns
                if e.eval is not None
            }
        )

        if (common_cols := set(data.columns).intersection(observables.columns)) != {"group_id"}:
            observables = observables.drop(columns=common_cols - {"group_id"})

        data_obs = data.merge(
            observables,
            on="group_id",
            indicator=True,
            how="outer",
        )

        self.info("Data obs", data_obs.describe())

        if any(selection := data_obs["_merge"] == "left_only"):
            raise ObservationWithoutObservable(data_obs[selection])

        if any(selection := data_obs["_merge"] == "right_only"):
            raise ObservableWithoutObservation(data_obs[selection])

        self.upload_instances(source, data_obs)

        return self.reset()

    def solve_observable(
        self,
        reliability: str,
        class_uuid: UUID,
        scale_uuid: UUID,
        period_uuid: UUID,
        group_uuid: UUID,
        source_uuid: UUID,
        group_id: str,
        group_parent_id: str,
        geometry: str,
        name: str,
        description: str,
        **_,
    ):
        resp = self.geoecon_api.get_observable(
            group_id=group_id,
            period_uuid=period_uuid,
            group_uuid=group_uuid,
            source_uuid=source_uuid,
        )
        if resp is None:
            resp = self.geoecon_api.new_observable(
                reliability=reliability,
                class_uuid=class_uuid,
                scale_uuid=scale_uuid,
                period_uuid=period_uuid,
                group_uuid=group_uuid,
                source_uuid=source_uuid,
                group_id=group_id,
                group_parent_id=group_parent_id,
                geometry=geometry,
                name=name,
                description=description,
            )
        return resp

    def upload_instances(self, source: Source, data_obs: pd.DataFrame):
        group_by_cols = self.group_by_cols(source)

        layers = data_obs.groupby(
            group_by_cols,
            observed=True,
        )

        n_layers = len(layers)
        n_instances = n_layers * len(source.columns)

        logging.info(f"🏷️- #Instances {n_instances}")
        self.info("Layers", layers.describe())

        with ProcessLogger(source.slug) as pl:
            for (group_tuple, group), column in pl.stages(
                self,
                product(layers, sorted(source.columns, key=lambda c: c.name)),
                lambda group, column: "/".join(sorted(str(g) for g in group[0]))
                + ":"
                + column.name,
            ):
                group_dict = group[group_by_cols].iloc[0].to_dict()

                selected_columns = drop_duplicates(
                    ["group_id", "abstract_scale", column.name]
                    + self.column_refs(source, only_categorizables=True)
                )

                self.deploy_instance(
                    source,
                    column,
                    group[selected_columns].rename(columns={column.name: "value"}),
                    group_dict,
                )

        return self

    def upload_geodata(
        self,
        source: Source,
        geodata: gpd.GeoDataFrame,
        update_geometry=True,
    ):
        logging.info("🗺️🚧- Processing geometries")

        # La geometría llega "naive" (build_observables arma el GeoDataFrame sin crs, y
        # get_geometry hace wkt.loads sin CRS). to_crs() sobre geometría sin CRS revienta
        # ("Cannot transform naive geometries"). Las geometrías del warehouse son WGS84.
        if geodata.crs is None:
            geodata = geodata.set_crs(epsg=4326)

        geodata["geometry"] = (
            (
                geodata.make_valid()
                .to_crs(epsg=3857)
                .simplify(tolerance=source.shape.tolerance, preserve_topology=True)
                .to_crs(epsg=4326)
            )
            if source.shape.tolerance
            else geodata.make_valid().to_crs(epsg=4326)
        )

        # Fast path opcional (GIQMD_WH_CONN): para datasets grandes (p.ej. 357k celdas h3)
        # crear observables+geometrías uno por uno vía API es inviable (~horas) y el read
        # posterior tumba la API. Si hay conn directa al warehouse, escribir en bloque.
        if os.environ.get("GIQMD_WH_CONN"):
            self._bulk_upload_geodata(geodata)
            return self

        n_geometries = len(geodata)

        logging.info(f"🗺️- #Geometries %s", n_geometries)

        with ProcessLogger(source.slug) as pl:
            for row in pl.stages(
                self,
                geodata.sort_values("group_id").to_wkt().to_dict(orient="records"),
                lambda row: f"group_id:{row['group_id']}",
            ):
                obs = self.solve_observable(**{**row, "geometry": None})
                if update_geometry:
                    self.geoecon_api.upload_geometry(obs["uuid"], row["geometry"])

        return self

    def _bulk_upload_geodata(self, geodata):
        """Escritura bulk de observables + geometrías directo al warehouse (psycopg2).
        Reemplaza el loop por-fila de upload_geodata cuando GIQMD_WH_CONN está seteada.
        El geodata ya trae todos los campos resueltos (group_id, *_uuid, name, parent,
        geometry); solo genera un uuid por celda (geometry_uuid == observable uuid).
        Idempotente: saltea si los observables de (source,group,period) ya existen."""
        import psycopg2
        from psycopg2.extras import execute_values

        def _h(x):  # los uuids llegan con guiones; las columnas son bpchar(32)
            return str(x).replace("-", "")

        recs = geodata.to_wkt().to_dict(orient="records")
        if not recs:
            return
        geoms, obs = [], []
        for r in recs:
            u = _uuid.uuid4().hex
            pp = r["group_parent_id"]
            geoms.append((u, r["geometry"]))
            obs.append((
                u, r["description"], r["reliability"], r["name"],
                _h(r["class_uuid"]), _h(r["scale_uuid"]), _h(r["group_uuid"]),
                _h(r["period_uuid"]), _h(r["source_uuid"]), u, str(r["group_id"]),
                (None if (pp is None or isinstance(pp, float)) else str(pp)),
            ))
        conn = psycopg2.connect(os.environ["GIQMD_WH_CONN"])
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) FROM wh.observables "
                "WHERE source_uuid=%s AND group_uuid=%s AND period_uuid=%s",
                (obs[0][8], obs[0][6], obs[0][7]),
            )
            if cur.fetchone()[0]:
                logging.info("Bulk geodata: observables ya presentes, skip insert")
                return
            execute_values(
                cur,
                "INSERT INTO wh.geometries (uuid, geometry) VALUES %s",
                geoms,
                template="(%s, ST_GeomFromText(%s, 4326))",
                page_size=5000,
            )
            execute_values(
                cur,
                "INSERT INTO wh.observables (uuid, created_at, updated_at, description, "
                "reliability, name, class_uuid, scale_uuid, group_uuid, period_uuid, "
                "source_uuid, geometry_uuid, group_id, group_parent_id) VALUES %s",
                obs,
                template="(%s, now(), now(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                page_size=5000,
            )
            conn.commit()
            logging.info("Bulk geodata: %s observables+geometrías insertados", len(obs))
        finally:
            conn.close()

    def dimension_exploder(self, source: Source):
        df = self.read_source(source)

        def explode(column: Column):
            for dimension in column.dimensions:
                if isref(dimension.name):
                    for d in df[dimension.name.ref].unique():
                        yield Dimension(name=d, group=dimension.group)
                else:
                    yield dimension

        return explode
