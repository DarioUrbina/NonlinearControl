import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from termcolor import cprint,colored
from danpy.sb import dsb,get_terminal_width
from pendulum_eqns.init_muscle_activation_controlled_model import *

N_seconds = 4
N = N_seconds*10000 + 1
Time = np.linspace(0,N_seconds,N)
dt = Time[1]-Time[0]

def return_U_gaussian_activations_nearby(i,t,X,U,**kwargs):
    """
    Takes in current step (i), numpy.ndarray of time (t) of shape (N,), state numpy.ndarray (X) of shape (8,), and previous input numpy.ndarray (U) of shape (2,) and returns the input for this time step.

    First attempt will see what happens when the activations are restricted to the positive real domain.

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **kwargs
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1) Noise - must be an numpy.ndarray of shape (2,). Default is np.zeros((1,2)).

    2) Seed - must be a scalar value. Default is None.

    3) Bounds - must be a (2,2) list with each row in ascending order. Default is given by Activation_Bounds.

    4) MaxStep - must be a scalar (int or float). Default is MaxStep_Activation.

    """
    import random
    import numpy as np
    assert (np.shape(t) == (len(t),)) and (str(type(t)) == "<class 'numpy.ndarray'>"),\
     	"t must be a numpy.ndarray of shape (len(t),)."
    assert np.shape(X) == (8,) and str(type(X)) == "<class 'numpy.ndarray'>", "X must be a (8,) numpy.ndarray"
    assert np.shape(U) == (2,) and str(type(U)) == "<class 'numpy.ndarray'>", "U must be a (2,) numpy.ndarray"

    Noise = kwargs.get("Noise",np.zeros((2,)))
    assert np.shape(Noise) == (2,) and str(type(Noise)) == "<class 'numpy.ndarray'>", "Noise must be a (2,) numpy.ndarray"

    Seed = kwargs.get("Seed",None)
    assert type(Seed) in [float,int] or Seed is None, "Seed must be a float or an int or None."
    if Seed is not None:
    	np.random.seed(Seed)

    Bounds = kwargs.get("Bounds",Activation_Bounds)
    assert type(Bounds) == list and np.shape(Bounds) == (2,2), "Bounds for Muscle Activation Control must be a (2,2) list."
    assert Bounds[0][0]<Bounds[0][1],"Each set of bounds must be in ascending order."
    assert Bounds[1][0]<Bounds[1][1],"Each set of bounds must be in ascending order."

    MaxStep = kwargs.get("MaxStep",MaxStep_Activation)
    assert type(MaxStep) in [int,float], "MaxStep for Muscle Activation Controller should be an int or float."

    Coefficient1,Coefficient2,Constraint1 = return_constraint_variables(t[i],X)
    assert Coefficient1!=0 and Coefficient2!=0, "Error with Coefficients. Shouldn't both be zero"
    if Constraint1 < 0:
    	assert not(Coefficient1 > 0 and Coefficient2 > 0), "Infeasible activations. (Constraint1 < 0, Coefficient1 > 0, Coefficient2 > 0)"
    if Constraint1 > 0:
    	assert not(Coefficient1 < 0 and Coefficient2 < 0), "Infeasible activations. (Constraint1 > 0, Coefficient1 < 0, Coefficient2 < 0)"

    AllowableBounds_x = np.array([U[0]-MaxStep,U[0]+MaxStep])
    AllowableBounds_y = np.array([U[1]-MaxStep,U[1]+MaxStep])

    if Coefficient1 == 0:
        LowerBound_x = max(Bounds[0][0],AllowbaleBounds_x[0])
        UpperBound_x = min(Bounds[0][1],AllowbaleBounds_x[1])
        LowerBound_y = Constraint1/Coefficient2
        UpperBound_y = Constraint1/Coefficient2
    elif Coefficient2 == 0:
        LowerBound_x = Constraint1/Coefficient1
        UpperBound_x = Constraint1/Coefficient1
        LowerBound_y = max(Bounds[1][0],AllowableBounds_y[0])
        UpperBound_y = min(Bounds[1][1],AllowableBounds_y[1])
    else:
        SortedAllowableBounds = np.sort([\
        							(Constraint1-Coefficient2*AllowableBounds_y[0])/Coefficient1,\
        							(Constraint1-Coefficient2*AllowableBounds_y[1])/Coefficient1\
        							])
        SortedBounds = np.sort([(Constraint1-Coefficient2*Bounds[1][0])/Coefficient1,\
        							(Constraint1-Coefficient2*Bounds[1][1])/Coefficient1])
        LowerBound_x = max(	Bounds[0][0],\
         					SortedBounds[0],\
        					AllowableBounds_x[0],\
        					SortedAllowableBounds[0]\
        				)
        UpperBound_x = min(	Bounds[0][1],\
         					SortedBounds[1],\
        					AllowableBounds_x[1],\
        					SortedAllowableBounds[1]\
        				)
        assert UpperBound_x >= LowerBound_x, "Error generating bounds. Not feasible!"

        SortedBounds_y = np.sort(
            [Constraint1/Coefficient2 - (Coefficient1/Coefficient2)*x_bound \
                for x_bound in [LowerBound_x,UpperBound_x]]
            )
        LowerBound_y = SortedBounds_y[0]
        UpperBound_y = SortedBounds_y[1]

    mu = 0
    sigma = 0.000625
    Feasible = False
    count = 0
    while Feasible == False:
        Next_U = (1/(Coefficient1**2+Coefficient2**2))\
                    *(
                        np.matrix([[Coefficient1],[Coefficient2]])
                        *(
                            Constraint1
                            - np.matrix([[Coefficient1,Coefficient2]])
                                * np.matrix([[U[0]],[U[1]]])
                        )
                    ) \
                + np.random.normal(mu,sigma) \
                    * np.matrix([[Coefficient2],[-Coefficient1]]) \
                    / np.sqrt(Coefficient1**2 + Coefficient2**2) \
                + np.matrix([[U[0]],[U[1]]])
        if (LowerBound_x <= Next_U[0,0] <= UpperBound_x) \
            and (LowerBound_y <= Next_U[1,0] <= UpperBound_y):
            Feasible = True
        else:
            count += 1
            if count > 100:
                Next_U = (1/(Coefficient1**2+Coefficient2**2))\
                            *(
                                np.matrix([[Coefficient1],[Coefficient2]])
                                *(
                                    Constraint1
                                    - np.matrix([[Coefficient1,Coefficient2]])
                                        * np.matrix([[U[0]],[U[1]]])
                                )
                            ) \
                        + np.matrix([[U[0]],[U[1]]])
                raise Exception("Hard time finding next input. Try increasing sigma (Currently: sigma = " + str(sigma) + ").")

    return(np.array([Next_U[0,0],Next_U[1,0]]))

def run_sim_gauss_act(**kwargs):
    """
    Runs one simulation for NEARBY ACTIVATION BY GAUSSIAN DISTRIBUTION control.

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **kwargs
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1) Bounds - must be a (2,2) list with each row in ascending order. Default is given by Tension_Bounds.

    2) InitialAngularAcceleration - must be a float or an int. Default is 0 (starting from rest).

    3) thresh - must be an int. Default is 25.

    4) FixedInitialTension - will be passed to find_viable_initial_values and will fix the value of initial tension. Must be a (2,) numpy.ndarray. Run find_initial_tension outside of the loop for a given seed and then feed it through the pipeline.

    """
    thresh = kwargs.get("thresh",25)
    assert type(thresh)==int, "thresh should be an int as it is the number of attempts the program should run before stopping."

    AnotherIteration = True
    AttemptNumber = 1

    while AnotherIteration == True:
        X = np.zeros((8,N))
        InitialTension,InitialMuscleLengths,InitialActivations = \
        	find_viable_initial_values(**kwargs)
        X[:,0] = [
        	r(0),
        	dr(0),
        	InitialTension[0][0],
        	InitialTension[1][0],
        	InitialMuscleLengths[0],
        	InitialMuscleLengths[1],
        	0,
        	0]
        U = np.zeros((2,N))
        U[:,0] = InitialActivations

        AddNoise = False
        if AddNoise == True:
            np.random.seed(seed=None)
            NoiseArray = np.random.normal(loc=0.0,scale=0.2,size=(2,N))
        else:
            NoiseArray = np.zeros((2,N))

        try:
            cprint("Attempt #" + str(int(AttemptNumber)) + ":\n", 'green')
            statusbar = dsb(0,N-1,title=run_sim_gauss_act.__name__)
            for i in range(N-1):
                U[:,i+1] = return_U_gaussian_activations_nearby(i,Time,X[:,i],U[:,i],Noise = NoiseArray[:,i])
                X[:,i+1] = X[:,i] + dt*np.array([	dX1_dt(X[:,i]),\
                									dX2_dt(X[:,i]),\
                									dX3_dt(X[:,i]),\
                									dX4_dt(X[:,i]),\
                									dX5_dt(X[:,i]),\
                									dX6_dt(X[:,i]),\
                									dX7_dt(X[:,i],U=U[:,i+1]),\
                									dX8_dt(X[:,i],U=U[:,i+1])
                                                    ])
                statusbar.update(i)
            AnotherIteration = False
            return(X,U)
        except:
            print('\n')
            print(" "*(get_terminal_width()\
            			- len("...Attempt #" + str(int(AttemptNumber)) + " Failed. "))\
            			+ colored("...Attempt #" + str(int(AttemptNumber)) + " Failed. \n",'red'))
            AttemptNumber += 1
            if AttemptNumber > thresh:
                AnotherIteration=False
                return(np.zeros((8,N)),np.zeros((2,N)))

def run_N_sim_gauss_act(**kwargs):

    NumberOfTrials = kwargs.get("NumberOfTrials",10)

    TotalX = np.zeros((NumberOfTrials,8,N))
    TotalU = np.zeros((NumberOfTrials,2,N))
    TerminalWidth = get_terminal_width()

    print("\n")
    for j in range(NumberOfTrials):
        TrialTitle = (
            "          Trial "
            + str(j+1)
            + "/" +str(NumberOfTrials)
            + "          \n")
        print(
            " "*int(TerminalWidth/2 - len(TrialTitle)/2)
            + colored(TrialTitle,'white',attrs=["underline","bold"])
            )
        TotalX[j],TotalU[j] = run_sim_gauss_act(**kwargs)

    i=0
    NumberOfSuccessfulTrials = NumberOfTrials
    while i < NumberOfSuccessfulTrials:
        if (TotalX[i]==np.zeros((8,np.shape(TotalX)[2]))).all():
            TotalX = np.delete(TotalX,i,0)
            TotalU = np.delete(TotalU,i,0)
            NumberOfSuccessfulTrials-=1
            if NumberOfSuccessfulTrials==0: raise ValueError("No Successful Trials!")
        else:
            i+=1

    print(
        "Number of Desired Runs: "
        + str(NumberOfTrials)
        + "\n"
        + "Number of Successful Runs: "
        + str(NumberOfSuccessfulTrials)
        + "\n"
    )
    return(TotalX,TotalU)

def plot_N_sim_gauss_act(t,TotalX,TotalU,**kwargs):
    Return = kwargs.get("Return",False)
    assert type(Return) == bool, "Return should either be True or False"

    ReturnError = kwargs.get("ReturnError",False)
    assert type(ReturnError)==bool, "ReturnError should be either True or False."

    fig1 = plt.figure(figsize = (9,7))
    fig1_title = "Underdetermined Forced-Pendulum Example"
    plt.title(fig1_title,fontsize=16,color='gray')
    statusbar = dsb(0,np.shape(TotalX)[0],title=(plot_N_sim_gauss_act.__name__ + " (" + fig1_title +")"))
    for j in range(np.shape(TotalX)[0]):
        plt.plot(t,(TotalX[j,0,:])*180/np.pi,'0.70',lw=2)
        statusbar.update(j)
    plt.plot(np.linspace(0,t[-1],1001),\
        	(r(np.linspace(0,t[-1],1001)))*180/np.pi,\
               'r')
    plt.xlabel("Time (s)")
    plt.ylabel("Desired Measure (Deg)")

    fig2 = plt.figure(figsize = (9,7))
    fig2_title = "Error vs. Time"
    plt.title(fig2_title)
    statusbar.reset(title=(plot_N_sim_gauss_act.__name__ + " (" + fig2_title +")"))
    for j in range(np.shape(TotalX)[0]):
        plt.plot(t, (r(t)-TotalX[j,0,:])*180/np.pi,color='0.70')
        statusbar.update(j)
    plt.xlabel("Time (s)")
    plt.ylabel("Error (Deg)")

    statusbar.reset(
        title=(
        	plot_N_sim_gauss_act.__name__
        	+ " (Plotting States, Inputs, and Muscle Length Comparisons)"
        	)
        )
    for j in range(np.shape(TotalX)[0]):
        if j == 0:
            fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Muscle Activations")
            fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Muscle Activations")
            fig5,Error = plot_l_m_comparison(
            t,TotalX[j],MuscleLengths=TotalX[j,4:6,:],
            Return=True,InputString="Muscle Activation",ReturnError=True
            )
            Error1 = Error[0][np.newaxis,:]
            Error2 = Error[1][np.newaxis,:]
        else:
            fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Muscle Activations",\
            	              Figure=fig3)
            fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Muscle Activations", \
            	              Figure = fig4)
            fig5,Error = plot_l_m_comparison(
            t,TotalX[j],MuscleLengths=TotalX[j,4:6,:],
            Return=True,InputString="Muscle Activation",ReturnError=True,
            Figure=fig5
            )
            Error1 = np.concatenate([Error1,Error[0][np.newaxis,:]],axis=0)
            Error2 = np.concatenate([Error2,Error[1][np.newaxis,:]],axis=0)
        statusbar.update(j)

    if Return == True:
        if ReturnError == True:
            return([fig1,fig2,fig3,fig4,fig5],[-Error1,-Error2])
        else:
            return([fig1,fig2,fig3,fig4,fig5])
    else:
        if ReturnError == True:
            plt.show()
            return([-Error1,-Error2])
        else:
            plt.show()

def plot_l_m_approximation_error_vs_tendon_tension(t,TotalX,Error,**kwargs):

    Return = kwargs.get("Return",False)
    assert type(Return) == bool, "Return should either be True or False"

    InitialTensions = kwargs.get("InitialTensions",[TotalX[0,2:4,0]])
    assert type(InitialTensions)==list,"InitialTensions must be a list or arrays"
    assert all(np.array([str(type(el))=="<class 'numpy.ndarray'>" for el in InitialTensions])), "All elements of InitialTensions must be a numpy.ndarray."

    NumberOfTensionTrials = len(InitialTensions)
    TendonTension1 = np.linspace(0.01*F_MAX1,0.9*F_MAX1,1001)
    TendonTension2 = np.linspace(0.01*F_MAX2,0.9*F_MAX2,1001)

    fig1,axes1 = plt.subplots(2,2,figsize=(10,8))
    plt.suptitle("Error from MTU Approx vs. Tendon Tension\nMuscle 1",fontsize=16)
    axes1[0][0].set_xlabel("Tendon Tension (N)")
    axes1[0][0].set_ylabel("Error (m)")
    axes1[0][0].set_xlim(
            TotalX[:,2,:].min()-0.1*(TotalX[:,2,:].max()-TotalX[:,2,:].min()),
            TotalX[:,2,:].max()+0.1*(TotalX[:,2,:].max()-TotalX[:,2,:].min()))
    axes1[0][0].set_ylim(
            Error[0].min()-0.1*(Error[0].max()-Error[0].min()),
            Error[0].max()+0.1*(Error[0].max()-Error[0].min()))
    # axes1[0][0].plot(TendonTension1,Error1,'0.70',lw=2)
    axes1[0][1].set_xlabel(r"$\longrightarrow$ Time (s) $\longrightarrow$")
    axes1[0][1].set_ylim(axes1[0][0].get_ylim())
    axes1[0][1].set_yticklabels(["" for el in axes1[0][1].get_yticks()])
    axes1[1][0].set_ylabel(r"$\longleftarrow$ Time (s) $\longleftarrow$")
    axes1[1][0].set_xlim(axes1[0][0].get_xlim())
    axes1[1][0].set_xticklabels(["" for el in axes1[0][0].get_xticks()])
    axes1[1][0].yaxis.tick_right()
    axes1[1][0].yaxis.set_label_position("right")
    axes1[1][0].set_yticks(-np.array(list(range(N_seconds+1))))
    axes1[1][0].set_yticklabels([str(-el) for el in axes1[1][0].get_yticks()])
    axes1[1][1].text(0.00,0.65,
        (r'error $= \frac{\tau}{k}\cdot\ln\left(\frac{e^{T_{1}(t)/\tau} - 1}{e^{T_{1}(0)/\tau} - 1} \right )$'),fontsize=20)
    axes1[1][1].text(0.075,0.475,
        (r'          - $(1 - \cos(\alpha_{1}))\left[l_{m,1}(t) - l_{m,1}(0) \right]$'), fontsize=16)
    axes1[1][1].text(0.15,0.325,
        (r'where,    $\tau = F_{MAX,1}\cdot c^T \cdot k^T$'),fontsize=14)
    axes1[1][1].text(0.15,0.15,
        (r'and    $k = \frac{F_{MAX,1}\cdot c^T}{l_{T_{o,1}}}$'),fontsize=14)
    axes1[1][1].axis('off')

    fig2,axes2 = plt.subplots(2,2,figsize=(10,8))
    plt.suptitle("Error from MTU Approx vs. Tendon Tension\nMuscle 2",fontsize=16)
    axes2[0][0].set_ylabel("Error (m)")
    axes2[0][0].set_xlabel("Tendon Tension (N)")
    axes2[0][0].set_xlim(
            TotalX[:,3,:].min()-0.1*(TotalX[:,3,:].max()-TotalX[:,3,:].min()),
            TotalX[:,3,:].max()+0.1*(TotalX[:,3,:].max()-TotalX[:,3,:].min()))
    axes2[0][0].set_ylim(
            Error[1].min()-0.1*(Error[1].max()-Error[1].min()),
            Error[1].max()+0.1*(Error[1].max()-Error[1].min()))
    # axes2[0][0].plot(TendonTension2,Error2,'0.70',lw=2)
    axes2[0][1].set_xlabel(r"$\longrightarrow$ Time (s) $\longrightarrow$")
    axes2[0][1].set_ylim(axes2[0][0].get_ylim())
    axes2[0][1].set_yticklabels(["" for el in axes2[0][1].get_yticks()])
    axes2[1][0].set_ylabel(r"$\longleftarrow$ Time (s) $\longleftarrow$")
    axes2[1][0].set_xlim(axes2[0][0].get_xlim())
    axes2[1][0].set_xticklabels(["" for el in axes2[0][0].get_xticks()])
    axes2[1][0].yaxis.tick_right()
    axes2[1][0].yaxis.set_label_position("right")
    axes2[1][0].set_yticks(-np.array(list(range(N_seconds+1))))
    axes2[1][0].set_yticklabels([str(-el) for el in axes1[1][0].get_yticks()])
    axes2[1][1].text(0.00,0.65,
        (r'error $= \frac{\tau}{k}\cdot\ln\left(\frac{e^{T_{2}(t)/\tau} - 1}{e^{T_{2}(0)/\tau} - 1} \right )$'),fontsize=20)
    axes2[1][1].text(0.075,0.475,
        (r'          - $(1 - \cos(\alpha_{2}))\left[l_{m,2}(t) - l_{m,2}(0) \right]$'), fontsize=16)
    axes2[1][1].text(0.15,0.325,
        (r'where,    $\tau = F_{MAX,2}\cdot c^T \cdot k^T$'),fontsize=14)
    axes2[1][1].text(0.15,0.15,
        (r'and    $k = \frac{F_{MAX,2}\cdot c^T}{l_{T_{o,2}}}$'),fontsize=14)
    axes2[1][1].axis('off')

    for i in range(NumberOfTensionTrials):
        error_function_1 = return_error_func_no_pennation(InitialTensions[i][0],F_MAX1,lTo1)
        error_function_2 = return_error_func_no_pennation(InitialTensions[i][1],F_MAX2,lTo2)
        Error1 = error_function_1(TendonTension1)
        Error2 = error_function_2(TendonTension2)
        axes1[0][0].plot(TendonTension1,Error1,str(1-InitialTensions[i][0]/F_MAX1),lw=2)
        axes2[0][0].plot(TendonTension2,Error2,str(1-InitialTensions[i][1]/F_MAX2),lw=2)

    statusbar = dsb(0,np.shape(TotalX)[0],
        title=plot_l_m_approximation_error_vs_tendon_tension.__name__)
    for i in range(np.shape(TotalX)[0]):
        axes1[0][0].plot(TotalX[i,2,:],Error[0][i])
        axes1[0][1].plot(Time,Error[0][i])
        axes1[1][0].plot(TotalX[i,2,:],-Time)

        axes2[0][0].plot(TotalX[i,3,:],Error[1][i])
        axes2[0][1].plot(Time,Error[1][i])
        axes2[1][0].plot(TotalX[i,3,:],-Time)
        statusbar.update(i)

    if Return == True:
        return([fig1,fig2])
    else:
        plt.show()

def plot_l_m_error_manifold(t,TotalX,Error,**kwargs):

    Return = kwargs.get("Return",False)
    assert type(Return) == bool, "Return should either be True or False"

    InitialTensions = kwargs.get("InitialTensions",[TotalX[0,2:4,0]])
    assert type(InitialTensions)==list,"InitialTensions must be a list or arrays"
    assert all(np.array([str(type(el))=="<class 'numpy.ndarray'>" for el in InitialTensions])), "All elements of InitialTensions must be a numpy.ndarray."

    NumberOfTensionTrials = len(InitialTensions)

    fig1 = plt.figure(figsize=(10,8))
    axes1_1 = fig1.add_subplot(221, projection='3d')
    axes1_2 = fig1.add_subplot(222)
    axes1_3 = fig1.add_subplot(223)
    axes1_4 = fig1.add_subplot(224)

    plt.suptitle("Error from MTU Approx vs. Tendon Tension\nMuscle 1",fontsize=16)

    fig2 = plt.figure(figsize=(10,8))
    axes2_1 = fig2.add_subplot(221, projection='3d')
    axes2_2 = fig2.add_subplot(222)
    axes2_3 = fig2.add_subplot(223)
    axes2_4 = fig2.add_subplot(224)

    plt.suptitle("Error from MTU Approx vs. Tendon Tension\nMuscle 2",fontsize=16)

    statusbar = dsb(0,np.shape(TotalX)[0],
        title=plot_l_m_approximation_error_vs_tendon_tension.__name__)
    for i in range(np.shape(TotalX)[0]):
        axes1_1.plot(TotalX[i,4,:],TotalX[i,2,:],Error[0][i])
        axes1_2.plot(Time,Error[0][i])
        axes1_3.plot(TotalX[i,2,:],-Time)

        axes2_1.plot(TotalX[i,5,:],TotalX[i,3,:],Error[1][i])
        axes2_2.plot(Time,Error[1][i])
        axes2_3.plot(TotalX[i,3,:],-Time)
        statusbar.update(i)

    for i in range(TotalX.shape[0]):
        error_function_1 = \
                return_error_func(TotalX[i,2,0],TotalX[i,4,0],F_MAX1,lTo1,α1)
        error_function_2 = \
                return_error_func(TotalX[i,3,0],TotalX[i,5,0],F_MAX2,lTo2,α2)

        MinimumTension1 = TotalX[:,2,:].min()
        MaximumTension1 = TotalX[:,2,:].max()
        Tension1Range = TotalX[:,2,:].max() - TotalX[:,2,:].min()
        TendonTension1 = np.linspace(
                    MinimumTension1 - 0.05*Tension1Range,
                    MaximumTension1 + 0.05*Tension1Range,
                    1001
                    )

        MinimumMuscleLength1 = TotalX[:,4,:].min()
        MaximumMuscleLength1 = TotalX[:,4,:].max()
        MuscleLength1Range = TotalX[:,4,:].max() - TotalX[:,4,:].min()
        MuscleLength1 = np.linspace(
                    MinimumMuscleLength1 - 0.05*MuscleLength1Range,
                    MaximumMuscleLength1 + 0.05*MuscleLength1Range,
                    1001
                    )

        MuscleLength1Mesh, TendonTension1Mesh = \
                np.meshgrid(MuscleLength1,TendonTension1)
        Error1 = \
                error_function_1(TendonTension1Mesh,MuscleLength1Mesh)

        MinimumTension2 = TotalX[:,3,:].min()
        MaximumTension2 = TotalX[:,3,:].max()
        Tension2Range = TotalX[:,3,:].max() - TotalX[:,3,:].min()
        TendonTension2 = np.linspace(
                    MinimumTension2 - 0.05*Tension2Range,
                    MaximumTension2 + 0.05*Tension2Range,
                    1001
                    )

        MinimumMuscleLength2 = TotalX[:,5,:].min()
        MaximumMuscleLength2 = TotalX[:,5,:].max()
        MuscleLength2Range = TotalX[:,5,:].max() - TotalX[:,5,:].min()
        MuscleLength2 = np.linspace(
                    MinimumMuscleLength2 - 0.05*MuscleLength2Range,
                    MaximumMuscleLength2 + 0.05*MuscleLength2Range,
                    1001
                    )

        MuscleLength2Mesh, TendonTension2Mesh = \
                np.meshgrid(MuscleLength2,TendonTension2)
        Error2 = \
                error_function_2(TendonTension2Mesh,MuscleLength2Mesh)

        axes1_1.plot_surface(MuscleLength1Mesh,
                            TendonTension1Mesh,
                            Error1,
                            color=str(np.linspace(0.25,0.75,TotalX.shape[0])[i]))
        axes2_1.plot_surface(MuscleLength2Mesh,
                            TendonTension2Mesh,
                            Error2,
                            color=str(np.linspace(0.25,0.75,TotalX.shape[0])[i]))

    axes1_1.set_xlabel("Muscle Length (m)")
    axes1_1.set_ylabel("Tendon Tension (N)")
    axes1_1.set_zlabel("Error (m)")
    axes1_2.set_xlabel(r"$\longrightarrow$ Time (s) $\longrightarrow$")
    axes1_2.set_ylim(axes1_1.get_zlim())
    # axes1_2.set_yticklabels(["" for el in axes1_2.get_yticks()])
    axes1_3.set_ylabel(r"$\longleftarrow$ Time (s) $\longleftarrow$")
    axes1_3.set_xlim(axes1_1.get_ylim())
    # axes1_3.set_xticklabels(["" for el in axes1_1.get_xticks()])
    axes1_3.yaxis.tick_right()
    axes1_3.yaxis.set_label_position("right")
    axes1_3.set_yticks(-np.array(list(range(N_seconds+1))))
    axes1_3.set_yticklabels([str(-el) for el in axes1_3.get_yticks()])
    axes1_4.text(0.00,0.65,
        (r'error $= \frac{\tau}{k}\cdot\ln\left(\frac{e^{T_{1}(t)/\tau} - 1}{e^{T_{1}(0)/\tau} - 1} \right )$'),fontsize=20)
    axes1_4.text(0.075,0.475,
        (r'          - $(1 - \cos(\alpha_{1}))\left[l_{m,1}(t) - l_{m,1}(0) \right]$'), fontsize=16)
    axes1_4.text(0.15,0.325,
        (r'where,    $\tau = F_{MAX,1}\cdot c^T \cdot k^T$'),fontsize=14)
    axes1_4.text(0.15,0.15,
        (r'and    $k = \frac{F_{MAX,1}\cdot c^T}{l_{T_{o,1}}}$'),fontsize=14)
    axes1_4.axis('off')

    axes2_1.set_xlabel("Muscle Length (m)")
    axes2_1.set_ylabel("Tendon Tension (N)")
    axes2_1.set_zlabel("Error (m)")
    axes2_2.set_xlabel(r"$\longrightarrow$ Time (s) $\longrightarrow$")
    axes2_2.set_ylim(axes2_1.get_zlim())
    # axes2_2.set_yticklabels(["" for el in axes2_2.get_yticks()])
    axes2_3.set_ylabel(r"$\longleftarrow$ Time (s) $\longleftarrow$")
    axes2_3.set_xlim(axes2_1.get_ylim())
    # axes2_3.set_xticklabels(["" for el in axes2_1.get_xticks()])
    axes2_3.yaxis.tick_right()
    axes2_3.yaxis.set_label_position("right")
    axes2_3.set_yticks(-np.array(list(range(N_seconds+1))))
    axes2_3.set_yticklabels([str(-el) for el in axes1_3.get_yticks()])
    axes2_4.text(0.00,0.65,
        (r'error $= \frac{\tau}{k}\cdot\ln\left(\frac{e^{T_{2}(t)/\tau} - 1}{e^{T_{2}(0)/\tau} - 1} \right )$'),fontsize=20)
    axes2_4.text(0.075,0.475,
        (r'          - $(1 - \cos(\alpha_{2}))\left[l_{m,2}(t) - l_{m,2}(0) \right]$'), fontsize=16)
    axes2_4.text(0.15,0.325,
        (r'where,    $\tau = F_{MAX,2}\cdot c^T \cdot k^T$'),fontsize=14)
    axes2_4.text(0.15,0.15,
        (r'and    $k = \frac{F_{MAX,2}\cdot c^T}{l_{T_{o,2}}}$'),fontsize=14)
    axes2_4.axis('off')

    if Return == True:
        return([fig1,fig2])
    else:
        plt.show()

def return_error(T,l_m,F_MAX,lTo,α):
    tau = F_MAX*cT*kT
    alpha = F_MAX*cT/lTo
    error = (tau/alpha)*np.log((np.exp(T/tau) - 1)/(np.exp(T[0]/tau) - 1)) \
                + (np.cos(α) - 1)*(l_m - l_m[0])
    return(error)

def return_error_func(T_o,l_mo,F_MAX,lTo,α):
    tau = F_MAX*cT*kT
    alpha = F_MAX*cT/lTo
    def error_func(T,l_m):
        return((tau/alpha)*np.log((np.exp(T/tau) - 1)/(np.exp(T_o/tau) - 1))
                    + (np.cos(α) - 1)*(l_m - l_mo))
    return(error_func)

def return_error_no_pennation(T,F_MAX,lTo):
    tau = F_MAX*cT*kT
    alpha = F_MAX*cT/lTo
    error = (tau/alpha)*np.log((np.exp(T/tau) - 1)/(np.exp(T[0]/tau) - 1))
    return(error)

def return_error_func_no_pennation(T_o,F_MAX,lTo):
    tau = F_MAX*cT*kT
    alpha = F_MAX*cT/lTo
    def error_func(T):
        return((tau/alpha)*np.log((np.exp(T/tau) - 1)/(np.exp(T_o/tau) - 1)))
    return(error_func)
