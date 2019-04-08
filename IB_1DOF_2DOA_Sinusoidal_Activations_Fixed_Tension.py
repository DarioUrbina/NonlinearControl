from pendulum_eqns.sim_eqns_ActIB_sinusoidal_activations import *
from useful_functions import *
import pickle

X_o = np.array([r(0),dr(0)])
InitialTensions = [return_initial_tension(
                        X_o,
                        ReturnMultipleInitialTensions=False,
                        Bounds = [[0,0.4*F_MAX1],[0,0.4*F_MAX2]],
                        InitialAngularAcceleration=0
                        )]
NumberOfTensionTrials = 1
NumberOfTrials = 1
InitialTensionsFromSuccessfulTrials = []
TerminalWidth = get_terminal_width()
count = 0
for i in range(NumberOfTensionTrials):
    try:
        TensionTrialTitle = (
            "          Tension Setting "
            + str(i+1)
            + "/" +str(NumberOfTensionTrials)
            + "          \n")
        print(
        	" "*int(TerminalWidth/2 - len(TensionTrialTitle)/2)
        	+ colored(TensionTrialTitle,'blue',attrs=["underline","bold"])
        	)

        TotalX_temp,TotalU_temp = run_N_sim_IB_sinus_act(
                NumberOfTrials=NumberOfTrials,
                FixedInitialTension=InitialTensions[i],
                Amp="Scaled",
                Freq=1,
                InitialAngularAcceleration=0,
                InitialAngularSnap=0
                )
        _,Error_temp = plot_N_sim_IB_sinus_act(
                Time,TotalX_temp,
                TotalU_temp,Return=True,
                ReturnError=True)
        plt.close('all')
        count+=1

        if count == 1:
            TotalX = TotalX_temp
            TotalU = TotalU_temp
            Error1 = Error_temp[0]
            Error2 = Error_temp[1]
            Error = [Error1,Error2]
            InitialTensionsFromSuccessfulTrials.append(TotalX_temp[0,2:4,0])
        else:
            TotalX = np.concatenate([TotalX,TotalX_temp],axis=0)
            TotalU = np.concatenate([TotalU,TotalU_temp],axis=0)
            Error1 = np.concatenate([Error1,Error_temp[0]],axis=0)
            Error2 = np.concatenate([Error2,Error_temp[1]],axis=0)
            Error = [Error1,Error2]
            InitialTensionsFromSuccessfulTrials.append(TotalX_temp[0,2:4,0])
    except:
        print("Trial " + str(i+1) + " Failed...")

print("Number of Total Trials: " + str(NumberOfTensionTrials) + "\n")
print(
    "Number of Successful Trials: "
    + str(len(InitialTensionsFromSuccessfulTrials))
    )

if len(InitialTensions) != 0:
    figs = plot_N_sim_IB_sinus_act(Time,TotalX,TotalU,Return=True)

    additional_figs = plot_l_m_approximation_error_vs_tendon_tension(
                            Time,TotalX,
                            Error,Return=True,
                            InitialTensions=InitialTensionsFromSuccessfulTrials
                            )
    # plt.show()

    save_figures("output_figures/integrator_backstepping_sinusoidal_activations_fixed_tensions/","1DOF_2DOA_v1.0",SaveAsPDF=True)
    plt.close('all')
    FormatedSaveData = {
            "States" : TotalX,
            "Input" : TotalU,
            "Error" : Error,
            "Initial Tensions" : InitialTensionsFromSuccessfulTrials
            }
    pickle.dump(
        FormatedSaveData,
        open(
            "output_figures/integrator_backstepping_sinusoidal_activations_fixed_tensions/output.pkl",
            "wb"
            )
        )
else:
    print("All Trials Unsuccessful...")
