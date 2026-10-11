# Independent ENTH bounded-run analysis

Status: **partial_run_physical_checks_passed**.

The run was interrupted before 100 ps; available partial-run physical checks passed.

## Checks

- `all_stage_logs_present`: **True**
- `no_lincs_or_constraint_warnings_any_stage`: **True**
- `no_fatal_errors_any_stage`: **True**
- `no_nonfinite_tokens_any_stage`: **True**
- `requested_100ps_dynamics_completed`: **False**
- `each_stage_reached_expected_time`: **False**
- `minimization_converged_below_requested_fmax`: **True**
- `finite_energy_observables`: **True**
- `temperature_in_broad_target_band`: **True**
- `positive_limited_volume`: **True**
- `membrane_leaflets_and_pip2`: **True**
- `h0_dssp_positive_control`: **True**

## Run completion

{
  "gmx_check_returncode": 0,
  "gmx_check_excerpt": "Checking file npt.xtc\n\n           :-) GROMACS - gmx check, 2023.3-Ubuntu_2023.3_1ubuntu3 (-:\n\nExecutable:   /usr/bin/gmx\nData prefix:  /usr\nWorking dir:  /home/gym/agent-gym-md/validation-007/run\nCommand line:\n  gmx check -f npt.xtc\n\n\nReading frame       0 time    0.000   \n# Atoms  39045\nPrecision 0.001 (nm)\n\nReading frame       1 time    2.000   \nReading frame       2 time    4.000   \nReading frame       3 time    6.000   \nReading frame       4 time    8.000   \nLast frame          4 time    8.000   \n\n\nItem        #frames Timestep (ps)\nStep             5    2\nTime             5    2\nLambda           0\nCoords           5    2\nVelocities       0\nForces           0\nBox              5    2\n\nGROMACS reminds you: \"And I Will Strike Down Upon Thee With Great Vengeance and With Furious Anger Those Who Attempt to Poison and Destroy My Brothers.\" (Pulp Fiction)\n\n",
  "final_gro_time_ps": 8.0,
  "last_valid_frame_recovery_returncode": 0,
  "trajectory_parsed_times_ps": [
    4.0,
    6.0,
    8.0,
    8.0
  ],
  "release_mdp_nsteps": 40000,
  "release_mdp_dt_ps": 0.002,
  "release_duration_ps": 80.0,
  "observed_stage_local_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 10.0,
    "npt_release": 8.0
  },
  "observed_cumulative_stage_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 20.0,
    "npt_release": 28.0
  },
  "expected_cumulative_stage_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 20.0,
    "npt_release": 100.0
  },
  "full_requested_run_duration_ps": 100.0,
  "release_finished_marker": true,
  "time_limit_marker": true,
  "observed_last_time_ps": 28.0,
  "completion_check": false,
  "stage_time_checks": {
    "nvt": true,
    "npt_restraint": true,
    "npt_release": false
  },
  "observed_stage_durations": {
    "nvt": {
      "observed_duration_ps": 10.0,
      "observed_steps_estimate": 5000,
      "requested_steps": 5000,
      "requested_duration_ps": 10.0
    },
    "npt_restraint": {
      "observed_duration_ps": 10.0,
      "observed_steps_estimate": 5000,
      "requested_steps": 5000,
      "requested_duration_ps": 10.0
    },
    "npt_release": {
      "observed_duration_ps": 8.0,
      "observed_steps_estimate": 4000,
      "requested_steps": 40000,
      "requested_duration_ps": 80.0
    }
  }
}

## Energy labels and summaries

{
  "path": "/home/gym/agent-gym-md/validation-007/run/independent-energy.xvg",
  "columns_and_labels": [
    "Time (ps)",
    "Potential",
    "Temperature",
    "Pressure",
    "Volume"
  ],
  "sample_count": 43,
  "summary": {
    "Time (ps)": {
      "n": 43,
      "finite": true,
      "mean": 4.2,
      "min": 0.0,
      "max": 8.4,
      "first": 0.0,
      "last": 8.4
    },
    "Potential": {
      "n": 43,
      "finite": true,
      "mean": -305663.3851744186,
      "min": -307215.875,
      "max": -304111.65625,
      "first": -306127.40625,
      "last": -305823.71875
    },
    "Temperature": {
      "n": 43,
      "finite": true,
      "mean": 303.51381806976735,
      "min": 299.081726,
      "max": 307.158264,
      "first": 302.947784,
      "last": 303.42981
    },
    "Pressure": {
      "n": 43,
      "finite": true,
      "mean": 43.570229837209304,
      "min": -441.626251,
      "max": 405.868652,
      "first": 129.264801,
      "last": 96.877663
    },
    "Volume": {
      "n": 43,
      "finite": true,
      "mean": 378.1551606976744,
      "min": 377.087433,
      "max": 378.737793,
      "first": 377.087433,
      "last": 378.555878
    }
  },
  "time_first_ps": 0.0,
  "time_last_ps": 8.4,
  "finite_all_columns": true,
  "returncode": 0,
  "recent_20ps_temperature_K": {
    "n": 43,
    "finite": true,
    "mean": 303.51381806976735,
    "min": 299.081726,
    "max": 307.158264,
    "first": 302.947784,
    "last": 303.42981
  },
  "volume_fractional_first_to_last_change": 0.003894176446872021,
  "observed_labels": {
    "potential": "Potential",
    "temperature": "Temperature",
    "pressure": "Pressure",
    "volume": "Volume"
  }
}

## Membrane

{
  "status": "checked",
  "recognized_lipid_P_count": 113,
  "membrane_center_z_A": 30.835401777590874,
  "leaflet_separation_A": 38.03825255102041,
  "upper": {
    "POPC": 48,
    "PIP2": 1,
    "total": 49
  },
  "lower": {
    "POPC": 64,
    "PIP2": 0,
    "total": 64
  },
  "pbc_method": "Circular mean for membrane center; phosphate z displacements wrapped to [-Lz/2,Lz/2).",
  "checks": {
    "both_leaflets_present": true,
    "exactly_one_pip2": true,
    "pip2_in_upper_leaflet": true,
    "separation_plausible": true
  }
}

## H0 DSSP

{
  "runs": {
    "starting_structure_gromacs": {
      "output_bytes": 159,
      "frame_or_structure_rows": 1,
      "sequence_rows": [
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~"
      ],
      "alpha_counts": [
        0
      ],
      "first18_alpha_fraction": [
        0.0
      ],
      "state_counts_per_first18": [
        {
          "~": 5,
          "S": 13
        }
      ],
      "returncode": 0
    },
    "trajectory_gromacs": {
      "output_bytes": 795,
      "frame_or_structure_rows": 5,
      "sequence_rows": [
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPP~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~SSSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~SSSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSS~SSSPP~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSS~~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSSS~SS~~~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~"
      ],
      "alpha_counts": [
        0,
        0,
        0,
        0,
        0
      ],
      "first18_alpha_fraction": [
        0.0,
        0.0,
        0.0,
        0.0,
        0.0
      ],
      "state_counts_per_first18": [
        {
          "~": 5,
          "S": 13
        },
        {
          "~": 5,
          "S": 13
        },
        {
          "~": 5,
          "S": 13
        },
        {
          "~": 5,
          "S": 13
        },
        {
          "~": 5,
          "S": 13
        }
      ],
      "returncode": 0
    },
    "starting_structure_dssp": {
      "output_bytes": 159,
      "frame_or_structure_rows": 1,
      "sequence_rows": [
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHT~SSSSPPPHHHHHHHHHHTTSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHHGGG~~~B~TTS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHH~~"
      ],
      "alpha_counts": [
        115
      ],
      "first18_alpha_fraction": [
        0.7777777777777778
      ],
      "state_counts_per_first18": [
        {
          "~": 3,
          "H": 14,
          "T": 1
        }
      ],
      "returncode": 0
    },
    "trajectory_dssp": {
      "output_bytes": 795,
      "frame_or_structure_rows": 5,
      "sequence_rows": [
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHT~SSSSPP~HHHHHHHHHHTTSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHTTGGG~~~B~TTS~B~SHHHHHHHHHHHHHHH~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHT~~SSSPPPHHHHHHHHHHTTSHHHHHHHHHHHHHHHT~~TTTHHHHHHHHHHHHHHHHHS~HHHHHHHHTTHHHHHHHTT~~~B~SSS~B~HHHHHHHHHHHHHHHH~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHHS~SSSPP~HHHHHHHHHGGGSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHTT~HHHHHTTTT~~~B~TTS~B~THHHHHHHHHHHHHHH~HHHHHHHHHHHHHHHHHHHTT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHHSS~SS~~~HHHHHHHHHHTSSHHHHHHHHHHHHHHTT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHGGGG~~~B~SSS~BSSHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHH~SSSSPPPHHHHHHHHHTTSSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHSHHHHHTTTT~~~B~SSS~BSHHHHHHHHHHHHHHHH~HHHHHHHHHHHHHHHHHHHHT~"
      ],
      "alpha_counts": [
        112,
        116,
        110,
        113,
        114
      ],
      "first18_alpha_fraction": [
        0.7222222222222222,
        0.7777777777777778,
        0.7222222222222222,
        0.7777777777777778,
        0.7222222222222222
      ],
      "state_counts_per_first18": [
        {
          "~": 3,
          "H": 13,
          "T": 2
        },
        {
          "~": 3,
          "H": 14,
          "T": 1
        },
        {
          "~": 3,
          "H": 13,
          "T": 2
        },
        {
          "~": 3,
          "H": 14,
          "T": 1
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
        }
      ],
      "returncode": 0
    }
  },
  "positive_control_has_alpha": true,
  "observed_residue_count": 158,
  "status": "validated_for_descriptive_assignments",
  "assumed_h0_first18_alpha_fraction_by_frame": [
    0.7222222222222222,
    0.7777777777777778,
    0.7222222222222222,
    0.7777777777777778,
    0.7222222222222222
  ],
  "assumed_h0_first18_states_by_frame": [
    {
      "~": 3,
      "H": 13,
      "T": 2
    },
    {
      "~": 3,
      "H": 14,
      "T": 1
    },
    {
      "~": 3,
      "H": 13,
      "T": 2
    },
    {
      "~": 3,
      "H": 14,
      "T": 1
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
    }
  ],
  "residue_mapping_status": "unverified proxy: first 18 residues in selected protein order; paper-specific H0 mapping unavailable",
  "interpretation_limit": "If neither starting-structure hydrogen mode yields alpha assignments, DSSP is unvalidated and no H0-disorder inference is made."
}

No 100-ps completion is claimed unless the trajectory and all stage durations confirm it. This is only a reconstructed inserted-state CPU validation; it does not reproduce Figure 4, assess the authors' pull protocol, validate the uncertain salt unit or exact H0 residue mapping, or establish biological agreement.
