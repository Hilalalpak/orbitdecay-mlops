use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use sgp4::{Elements, Constants};
use chrono::{DateTime, Utc};

fn parse_elements(line1: &str, line2: &str) -> Option<Elements> {
    Elements::from_tle(None, line1.as_bytes(), line2.as_bytes()).ok()
}

pub fn state_output(_: &[Field]) -> PolarsResult<Field> {
    Ok(Field::new("state_data", DataType::Struct(vec![
        Field::new("sgp4_error", DataType::Int32),
        Field::new("pos_x",      DataType::Float64),
        Field::new("pos_y",      DataType::Float64),
        Field::new("pos_z",      DataType::Float64),
        Field::new("vel_x",      DataType::Float64),
        Field::new("vel_y",      DataType::Float64),
        Field::new("vel_z",      DataType::Float64),
    ])))
}

#[polars_expr(output_type_func=state_output)]
fn propagate_state_vectors(inputs: &[Series]) -> PolarsResult<Series> {
    let tle1             = inputs[0].str()?;
    let tle2             = inputs[1].str()?;
    let target_epoch_str = inputs[2].str()?;

    let len = tle1.len();

    let mut errs = PrimitiveChunkedBuilder::<Int32Type>::new("sgp4_error", len);
    let mut px   = PrimitiveChunkedBuilder::<Float64Type>::new("pos_x", len);
    let mut py   = PrimitiveChunkedBuilder::<Float64Type>::new("pos_y", len);
    let mut pz   = PrimitiveChunkedBuilder::<Float64Type>::new("pos_z", len);
    let mut vx   = PrimitiveChunkedBuilder::<Float64Type>::new("vel_x", len);
    let mut vy   = PrimitiveChunkedBuilder::<Float64Type>::new("vel_y", len);
    let mut vz   = PrimitiveChunkedBuilder::<Float64Type>::new("vel_z", len);

    for ((l1_opt, l2_opt), ep_opt) in tle1
        .into_iter()
        .zip(tle2.into_iter())
        .zip(target_epoch_str.into_iter())
    {
        let mut success  = false;
        let mut err_code = 1i32;

        if let (Some(l1), Some(l2), Some(ep_str)) = (l1_opt, l2_opt, ep_opt) {
            if let Some(elements) = parse_elements(l1, l2) {
                if let Ok(constants) = Constants::from_elements(&elements) {
                    let dt_str = if ep_str.ends_with('Z') {
                        ep_str.replace('Z', "+00:00")
                    } else if !ep_str.contains('+') {
                        format!("{}+00:00", ep_str.trim().replace(' ', "T"))
                    } else {
                        ep_str.to_string()
                    };

                    if let Ok(target_dt) = DateTime::parse_from_rfc3339(&dt_str) {
                        let tle_epoch  = elements.datetime;
                        let diff_ms    = target_dt.with_timezone(&Utc).timestamp_millis()
                                         - tle_epoch.timestamp_millis();
                        let minutes    = diff_ms as f64 / 60_000.0;

                        if let Ok(pred) = constants.propagate(minutes) {
                            errs.append_value(0);
                            px.append_value(pred.position[0]);
                            py.append_value(pred.position[1]);
                            pz.append_value(pred.position[2]);
                            vx.append_value(pred.velocity[0]);
                            vy.append_value(pred.velocity[1]);
                            vz.append_value(pred.velocity[2]);
                            success = true;
                        } else {
                            err_code = 2;
                        }
                    }
                }
            }
        }

        if !success {
            errs.append_value(err_code);
            px.append_null(); py.append_null(); pz.append_null();
            vx.append_null(); vy.append_null(); vz.append_null();
        }
    }

    let out = StructChunked::new("state_data", &[
        errs.finish().into_series(),
        px.finish().into_series(),
        py.finish().into_series(),
        pz.finish().into_series(),
        vx.finish().into_series(),
        vy.finish().into_series(),
        vz.finish().into_series(),
    ])?;

    Ok(out.into_series())
}

use pyo3::prelude::*;

#[pymodule]
fn orbital_plugin(_py: Python, m: &PyModule) -> PyResult<()> {
    Ok(())
}
