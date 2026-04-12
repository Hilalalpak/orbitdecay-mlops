import polars as pl
from pathlib import Path

LIB_PATH = Path(__file__).parent


def propagate_state_vectors(
    tle1: pl.Expr,
    tle2: pl.Expr,
    target_epoch_dt: pl.Expr,
) -> pl.Expr:
    """
    Struct : {sgp4_error, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z}

        df.with_columns(
            propagate_state_vectors(
                pl.col("tle_line1"),
                pl.col("tle_line2"),
                pl.col("epoch_dt"),
            ).alias("state_data")
        ).unnest("state_data")
    """
    epoch_str = target_epoch_dt.dt.strftime("%Y-%m-%dT%H:%M:%S%.f")

    return tle1.register_plugin(
        lib=LIB_PATH,
        symbol="propagate_state_vectors",
        args=[tle2, epoch_str],
        is_elementwise=False,
    )