/// codette_core — Rust hot paths for Codette's FFT-heavy operations.
///
/// Ports the two most compute-intensive Python operations:
///   1. cocoon_stability_check()  — CocoonStabilityField FFT analysis (L4)
///   2. nexis_fft_analysis()      — NexisSignalEngine frequency spectrum (L2)
///
/// Both are pure numerical transforms with no Python-specific logic.
/// Python falls back to numpy when this crate is not compiled.
///
/// Build:
///   cd codette_core && maturin develop --release
///   (requires: pip install maturin)

use pyo3::prelude::*;
use rustfft::{FftPlanner, num_complex::Complex};
#[allow(unused_imports)]
use std::collections::HashSet;

// ---------------------------------------------------------------------------
// 1. Cocoon Stability Check (L4 of consciousness stack)
//    Mirrors CocoonStabilityField.text_to_spectrum() + check_stability()
//    Returns (is_stable: bool, energy_concentration: f64, top_freq_ratio: f64)
// ---------------------------------------------------------------------------

/// Analyse a text response for synthesis loop collapse.
///
/// Returns (is_stable, energy_concentration, unique_word_ratio)
/// is_stable = True means safe to continue; False means halt and fallback.
#[pyfunction]
fn cocoon_stability_check(
    text: &str,
    energy_threshold: f64,
    vocab_threshold: f64,
) -> PyResult<(bool, f64, f64)> {
    let fft_size: usize = 256;

    // Encode text as char codes (mod 256), same as Python version
    let char_codes: Vec<f64> = text
        .chars()
        .take(1000)
        .map(|c| (c as u32 % 256) as f64)
        .collect();

    if char_codes.is_empty() {
        return Ok((true, 0.0, 1.0));
    }

    // Pad to fft_size
    let mut padded: Vec<Complex<f64>> = vec![Complex::new(0.0, 0.0); fft_size];
    for (i, &v) in char_codes.iter().take(fft_size).enumerate() {
        padded[i] = Complex::new(v, 0.0);
    }

    // FFT
    let mut planner = FftPlanner::<f64>::new();
    let fft = planner.plan_fft_forward(fft_size);
    fft.process(&mut padded);

    // Power spectrum (magnitude squared)
    let power: Vec<f64> = padded.iter().map(|c| c.norm_sqr()).collect();
    let total_power: f64 = power.iter().sum();

    let energy_concentration = if total_power > 0.0 {
        // Ratio of top-10 frequencies to total power
        let mut sorted = power.clone();
        sorted.sort_by(|a, b| b.partial_cmp(a).unwrap());
        let top10: f64 = sorted.iter().take(10).sum();
        top10 / total_power
    } else {
        0.0
    };

    // Vocabulary diversity
    let words: Vec<&str> = text.split_whitespace().collect();
    let total_words = words.len();
    let unique_words = {
        let mut set = std::collections::HashSet::new();
        for w in &words {
            set.insert(w.to_lowercase());
        }
        set.len()
    };
    let unique_ratio = if total_words > 0 {
        unique_words as f64 / total_words as f64
    } else {
        1.0
    };

    let is_stable = energy_concentration < energy_threshold && unique_ratio >= vocab_threshold;

    Ok((is_stable, energy_concentration, unique_ratio))
}

// ---------------------------------------------------------------------------
// 2. Nexis FFT Analysis (L2 of consciousness stack)
//    Mirrors NexisSignalEngine._resonance_equation()
//    Returns Vec<f64> of real spectral components (first 8 frequencies)
// ---------------------------------------------------------------------------

/// Compute the FFT resonance spectrum for a text signal.
///
/// Returns the first 8 real-valued spectral components.
/// Used by NexisSignalEngine for harmonic intent analysis.
#[pyfunction]
fn nexis_fft_analysis(text: &str, salt: u32) -> PyResult<Vec<f64>> {
    let freqs: Vec<Complex<f64>> = text
        .chars()
        .filter(|c| c.is_alphabetic())
        .map(|c| {
            let val = ((c as u32 + salt) % 13) as f64;
            Complex::new(val, 0.0)
        })
        .collect();

    if freqs.is_empty() {
        return Ok(vec![0.0; 8]);
    }

    let n = freqs.len();
    let mut buffer = freqs;

    let mut planner = FftPlanner::<f64>::new();
    let fft = planner.plan_fft_forward(n);
    fft.process(&mut buffer);

    let result: Vec<f64> = buffer.iter().take(8).map(|c| c.re).collect();

    // Pad to 8 if text was very short
    let mut out = result;
    out.resize(8, 0.0);

    Ok(out)
}

// ---------------------------------------------------------------------------
// 3. Cosine similarity batch (used by SemanticTensionEngine)
//    Returns similarity score between two f64 vectors.
// ---------------------------------------------------------------------------

/// Compute cosine similarity between two vectors.
#[pyfunction]
fn cosine_similarity(a: Vec<f64>, b: Vec<f64>) -> PyResult<f64> {
    if a.len() != b.len() || a.is_empty() {
        return Ok(0.0);
    }
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return Ok(0.0);
    }
    Ok(dot / (norm_a * norm_b))
}

// ---------------------------------------------------------------------------
// Module registration
// ---------------------------------------------------------------------------

#[pymodule]
fn codette_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cocoon_stability_check, m)?)?;
    m.add_function(wrap_pyfunction!(nexis_fft_analysis, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_similarity, m)?)?;
    Ok(())
}
