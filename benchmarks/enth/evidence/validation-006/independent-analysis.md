# Independent ENTH bounded-run analysis

Status: **bounded_validation_failed_or_incomplete**.

One or more physical checks failed or were unavailable; see check details and raw logs.

## Checks

- `all_stage_logs_present`: **True**
- `no_lincs_or_constraint_warnings_any_stage`: **False**
- `no_fatal_errors_any_stage`: **True**
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
  "gmx_check_excerpt": "Checking file npt.xtc\n\n           :-) GROMACS - gmx check, 2023.3-Ubuntu_2023.3_1ubuntu3 (-:\n\nExecutable:   /usr/bin/gmx\nData prefix:  /usr\nWorking dir:  /home/gym/agent-gym-md/validation-006/run\nCommand line:\n  gmx check -f npt.xtc\n\n\nReading frame       0 time    0.000   \n# Atoms  39045\nPrecision 0.001 (nm)\n\nReading frame       1 time    2.000   \nReading frame       2 time    4.000   \nReading frame       3 time    6.000   \nReading frame       4 time    8.000   \nReading frame       5 time   10.000   \nReading frame       6 time   12.000   \nReading frame       7 time   14.000   \nReading frame       8 time   16.000   \nReading frame       9 time   18.000   \nReading frame      10 time   20.000   \nReading frame      11 time   22.000   \nReading frame      12 time   24.000   \nReading frame      13 time   26.000   \nReading frame      14 time   28.000   \nReading frame      15 time   30.000   \nReading frame      16 time   32.000   \nReading frame      17 time   34.000   \nReading frame      18 time   36.000   \nReading frame      19 time   38.000   \nLast frame         19 time   38.000   \n\n\nItem        #frames Timestep (ps)\nStep            20    2\nTime            20    2\nLambda           0\nCoords          20    2\nVelocities       0\nForces           0\nBox             20    2\n\nGROMACS reminds you: \"Uh-oh .... Right Again\" (Laurie Anderson)\n\n",
  "final_gro_time_ps": 38.0,
  "last_valid_frame_recovery_returncode": 0,
  "trajectory_parsed_times_ps": [
    36.0,
    38.0,
    38.0,
    20.0
  ],
  "release_mdp_nsteps": 40000,
  "release_mdp_dt_ps": 0.002,
  "release_duration_ps": 80.0,
  "observed_stage_local_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 10.0,
    "npt_release": 38.0
  },
  "observed_cumulative_stage_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 20.0,
    "npt_release": 58.0
  },
  "expected_cumulative_stage_times_ps": {
    "nvt": 10.0,
    "npt_restraint": 20.0,
    "npt_release": 100.0
  },
  "full_requested_run_duration_ps": 100.0,
  "release_finished_marker": false,
  "time_limit_marker": false,
  "observed_last_time_ps": 58.0,
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
      "observed_duration_ps": 38.0,
      "observed_steps_estimate": 19000,
      "requested_steps": 40000,
      "requested_duration_ps": 80.0
    }
  }
}

## Energy labels and summaries

{
  "path": "/home/gym/agent-gym-md/validation-006/run/independent-energy.xvg",
  "columns_and_labels": [
    "Time (ps)",
    "Potential",
    "Temperature",
    "Pressure",
    "Volume"
  ],
  "sample_count": 193,
  "summary": {
    "Time (ps)": {
      "n": 193,
      "finite": true,
      "mean": 19.200000000000003,
      "min": 0.0,
      "max": 38.4,
      "first": 0.0,
      "last": 38.4
    },
    "Potential": {
      "n": 193,
      "finite": true,
      "mean": -308705.8196243523,
      "min": -311558.375,
      "max": -305884.65625,
      "first": -306566.34375,
      "last": -311555.5
    },
    "Temperature": {
      "n": 193,
      "finite": true,
      "mean": 303.1818637253883,
      "min": 299.716492,
      "max": 307.542633,
      "first": 302.081573,
      "last": 301.599976
    },
    "Pressure": {
      "n": 193,
      "finite": true,
      "mean": 33.702088176165816,
      "min": -517.356018,
      "max": 500.722992,
      "first": 247.585999,
      "last": -109.896454
    },
    "Volume": {
      "n": 193,
      "finite": true,
      "mean": 377.89419494300506,
      "min": 376.244659,
      "max": 379.523163,
      "first": 376.244659,
      "last": 378.866364
    }
  },
  "time_first_ps": 0.0,
  "time_last_ps": 38.4,
  "finite_all_columns": true,
  "returncode": 0,
  "recent_20ps_temperature_K": {
    "n": 101,
    "finite": true,
    "mean": 303.12291154455454,
    "min": 299.745758,
    "max": 306.514771,
    "first": 302.743256,
    "last": 301.599976
  },
  "volume_fractional_first_to_last_change": 0.006968085625369536,
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
  "membrane_center_z_A": 30.604155217055975,
  "leaflet_separation_A": 37.52504464285714,
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
      "output_bytes": 3180,
      "frame_or_structure_rows": 20,
      "sequence_rows": [
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~S~SSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~S~SS~~~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSSS~SSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSSS~SSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSSS~SS~~~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSSSS~SS~~~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~SSS~~~SSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~SSSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~~SSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSSSSSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPPPSSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~SSSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~SSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSS~SS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSSPS~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~SSS~S~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~SSSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSS~SSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~",
        "~~SSSSSSSSSSSSS~~~SSSSSSSSSS~~SSS~~~SSSSSSSSSSSS~SSSSSSSSSSSSSSSS~~SS~~SSSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSS~~~~~SSS~~~SSSSSSSSSSSSSSSS~SSSSSSSSSSSSSSSSSSSS~~"
      ],
      "alpha_counts": [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
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
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
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
      "output_bytes": 3180,
      "frame_or_structure_rows": 20,
      "sequence_rows": [
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHH~S~SSPPPHHHHHHHHHTTTSHHHHHHHHHHHHHHHT~~TTTHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHGGGG~~~B~SSS~BSHHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHH~S~SS~~~HHHHHHHHHHTTSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHGGGG~~~B~TTS~BSSHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHH~~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHTSS~SSPPPHHHHHHHHHHTTSHHHHHHHHHHHHHHHS~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHTTHHHHHHGGG~~~B~SSS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHTT~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHSSS~SSPPPHHHHHHHHHTTSSHHHHHHHHHHHHHHHS~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHTTHHHHGGGGG~~~B~SSS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHTSS~SS~~~HHHHHHHHHTSSSHHHHHHHHHHHHHHHT~~TTTHHHHHHHHHHHHHHHHHS~HHHHHHHHTTHHHHGGGGG~~~B~SSS~BSSHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHTT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHTSS~SS~~~HHHHHHHHHGGGSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHTTSHHHHTTGGG~~~B~SSS~B~THHHHHHHHHHHHHHH~HHHHHHHHHHHHHHHHHHHHT~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHH~SSSSPPPHHHHHHHHHTTS~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHSHHHHHGGGG~~~B~SSS~B~THHHHHHHHHHHHHTT~HHHHHHHHHHHHHHHHHHHH~~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHH~SSSSPPPHHHHHHHHHTTSSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHGGGGG~~~B~SSS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHT~~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHT~~SSS~~~HHHHHHHHHTTSSHHHHHHHHHHHHHHHS~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHHHTT~~~B~TTS~BSHHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHH~~~SSPPPHHHHHHHHGGGGSHHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHHGGG~~~EETTTEE~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHT~SSSSPPPHHHHHHHHHHTTSHHHHHHHHHHHHHHHS~~GGGHHHHHHHHHHHHHHHHHS~THHHHHHHTTHHHHHHGGG~~~B~TTS~BSHHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHS~SSSSPPPHHHHHHHHGGGG~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHTS~HHHHHHHHHTHHHHHHGGG~~~B~TTS~BSSHHHHHHHHHHHHHHS~HHHHHHHHHHHHHHHHHHHH~~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHT~~SSS~~~HHHHHHHHHHTT~HHHHHHHHHHHHHHHS~~GGGHHHHHHHHHHHHHHHHHS~SHHHHHHHHTHHHHHGGGG~~~B~TTS~BSHHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHHT~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHH~SSSS~~~HHHHHHHHHGGG~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHGGGG~~~EETTTEE~HHHHHHHHHHHHHHTT~HHHHHHHHHHHHHHHHHHHTT~",
        "~HHHHHHHHHHHHHHT~~HHHHHHHHHH~SSSS~~~HHHHHHHHHGGG~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~THHHHHHHHTHHHHHTGGG~~~B~TTS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHH~~",
        "~HHHHHHHHHHHHHTT~~HHHHHHHHHT~SSSSPS~HHHHHHHHHGGG~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~THHHHHHHHTHHHHHTTTT~~~B~TTS~B~HHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHH~~",
        "~HHHHHHHHHHHHHH~~~HHHHHHHHHH~~SSS~S~HHHHHHHHHGGG~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHGGGG~~~EETTTEE~SHHHHHHHHHHHHHHT~HHHHHHHHHHHHHHHHHHHT~~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHS~SSSS~~~HHHHHHHHHTTS~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHHHHHHHHGGG~~~B~TTS~B~HHHHHHHHHHHHHHTT~HHHHHHHHHHHHHHHHHHHH~~",
        "~~HHHHHHHHHHHHHT~~HHHHHHHHHS~SSSS~~~HHHHHHHHHTTS~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHHTHHHHHHGGG~~~B~TTS~B~HHHHHHHHHHHHHHTT~HHHHHHHHHHHHHHHHHHHH~~",
        "~THHHHHHHHHHHHHT~~HHHHHHHHHT~~SSS~~~HHHHHHHHHTTS~HHHHHHHHHHHHHHHT~~GGGHHHHHHHHHHHHHHHHHS~HHHHHHHHTTHHHHHGGGG~~~B~TTS~B~HHHHHHHHHHHHHHHS~HHHHHHHHHHHHHHHHHHHH~~"
      ],
      "alpha_counts": [
        114,
        114,
        113,
        110,
        109,
        110,
        111,
        111,
        114,
        113,
        112,
        111,
        113,
        111,
        113,
        111,
        112,
        113,
        112,
        111
      ],
      "first18_alpha_fraction": [
        0.7777777777777778,
        0.7777777777777778,
        0.7777777777777778,
        0.7222222222222222,
        0.7777777777777778,
        0.7777777777777778,
        0.7222222222222222,
        0.7222222222222222,
        0.7222222222222222,
        0.7222222222222222,
        0.7222222222222222,
        0.7777777777777778,
        0.7777777777777778,
        0.7222222222222222,
        0.7777777777777778,
        0.7222222222222222,
        0.7777777777777778,
        0.7222222222222222,
        0.7222222222222222,
        0.7222222222222222
      ],
      "state_counts_per_first18": [
        {
          "~": 3,
          "H": 14,
          "T": 1
        },
        {
          "~": 3,
          "H": 14,
          "T": 1
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
          "~": 3,
          "H": 14,
          "T": 1
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
        },
        {
          "~": 3,
          "H": 13,
          "T": 2
        },
        {
          "~": 3,
          "H": 13,
          "T": 2
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
          "~": 3,
          "H": 14,
          "T": 1
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
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
          "~": 4,
          "H": 14
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
        },
        {
          "~": 4,
          "H": 13,
          "T": 1
        },
        {
          "~": 3,
          "T": 2,
          "H": 13
        }
      ],
      "returncode": 0
    }
  },
  "positive_control_has_alpha": true,
  "observed_residue_count": 158,
  "status": "validated_for_descriptive_assignments",
  "assumed_h0_first18_alpha_fraction_by_frame": [
    0.7777777777777778,
    0.7777777777777778,
    0.7777777777777778,
    0.7222222222222222,
    0.7777777777777778,
    0.7777777777777778,
    0.7222222222222222,
    0.7222222222222222,
    0.7222222222222222,
    0.7222222222222222,
    0.7222222222222222,
    0.7777777777777778,
    0.7777777777777778,
    0.7222222222222222,
    0.7777777777777778,
    0.7222222222222222,
    0.7777777777777778,
    0.7222222222222222,
    0.7222222222222222,
    0.7222222222222222
  ],
  "assumed_h0_first18_states_by_frame": [
    {
      "~": 3,
      "H": 14,
      "T": 1
    },
    {
      "~": 3,
      "H": 14,
      "T": 1
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
      "~": 3,
      "H": 14,
      "T": 1
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
    },
    {
      "~": 3,
      "H": 13,
      "T": 2
    },
    {
      "~": 3,
      "H": 13,
      "T": 2
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
      "~": 3,
      "H": 14,
      "T": 1
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
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
      "~": 4,
      "H": 14
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
    },
    {
      "~": 4,
      "H": 13,
      "T": 1
    },
    {
      "~": 3,
      "T": 2,
      "H": 13
    }
  ],
  "residue_mapping_status": "unverified proxy: first 18 residues in selected protein order; paper-specific H0 mapping unavailable",
  "interpretation_limit": "If neither starting-structure hydrogen mode yields alpha assignments, DSSP is unvalidated and no H0-disorder inference is made."
}

No 100-ps completion is claimed unless the trajectory and all stage durations confirm it. This is only a reconstructed inserted-state CPU validation; it does not reproduce Figure 4, assess the authors' pull protocol, validate the uncertain salt unit or exact H0 residue mapping, or establish biological agreement.
