import numpy as np
import matplotlib.pyplot as plt
from termcolor import cprint,colored
from danpy.sb import dsb,get_terminal_width
from pendulum_eqns.init_tendon_tension_controlled_model import *

N_seconds = 1
N = N_seconds*10000 + 1
Time = np.linspace(0,N_seconds,N)
dt = Time[1]-Time[0]

def return_U_random_tensions(i,t,X,U,**kwargs):
    """
    Takes in time scalar (float) (t), state numpy.ndarray (X) of shape (2,), and previous input numpy.ndarray (U) of shape (2,) and returns the input for this time step.

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **kwargs
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1) Noise - must be an numpy.ndarray of shape (2,). Default is np.zeros((1,2)).

    2) Seed - must be a scalar value. Default is None.

    3) Bounds - must be a (2,2) list with each row in ascending order. Default is given by Tension_Bounds.

    4) MaxStep - must be a scalar (int or float). Default is MaxStep_Tension.

    """
    import random
    import numpy as np

    assert np.shape(X) == (2,) and str(type(X)) == "<class 'numpy.ndarray'>", "X must be a (2,) numpy.ndarray"
    assert np.shape(U) == (2,) and str(type(U)) == "<class 'numpy.ndarray'>", "U must be a (2,) numpy.ndarray"

    dt = t[1]-t[0]

    Noise = kwargs.get("Noise",np.zeros((2,)))
    assert np.shape(Noise) == (2,) and str(type(Noise)) == "<class 'numpy.ndarray'>", "Noise must be a (2,) numpy.ndarray"

    Seed = kwargs.get("Seed",None)
    assert type(Seed) in [float,int] or Seed is None, "Seed must be a float or an int or None."
    np.random.seed(Seed)

    Bounds = kwargs.get("Bounds",Tension_Bounds)
    assert type(Bounds) == list and np.shape(Bounds) == (2,2), "Bounds for Tension Control must be a (2,2) list."
    assert Bounds[0][0]<Bounds[0][1],"Each set of bounds must be in ascending order."
    assert Bounds[1][0]<Bounds[1][1],"Each set of bounds must be in ascending order."

    MaxStep = kwargs.get("MaxStep",MaxStep_Tension)
    assert type(MaxStep) in [int,float], "MaxStep for Tension Controller should be an int or float."

    Coefficient1,Coefficient2,Constraint1 = return_constraint_variables(t[i],X)

    if Constraint1 != 0:
    	assert Coefficient1!=0 and Coefficient2!=0, "Error with Coefficients. Shouldn't be zero with nonzero constraint."
    else:
    	assert Coefficient1!=0 and Coefficient2!=0, "Error with Constraint. 0 = 0 implies all inputs valid."

    AllowableBounds_x = np.array([U[0]-MaxStep,U[0]+MaxStep])
    AllowableBounds_y = np.array([U[1]-MaxStep,U[1]+MaxStep])

    if Coefficient1 == 0:
        LowerBound_x = max(Bounds[0][0],AllowbaleBounds_x[0])
        UpperBound_x = min(Bounds[0][1],AllowbaleBounds_x[1])
        FeasibleInput1 = (UpperBound_x-LowerBound_x)*np.random.rand() + LowerBound_x
        FeasibleInput2 = Constraint1/Coefficient2
    elif Coefficient2 == 0:
        LowerBound_y = max(Bounds[1][0],AllowableBounds_y[0])
        UpperBound_y = min(Bounds[1][1],AllowableBounds_y[1])
        FeasibleInput1 = Constraint1/Coefficient1
        FeasibleInput2 = (UpperBound_y-LowerBound_y)*np.random.rand() + LowerBound_y
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
        # if UpperBound_x < LowerBound_x: import ipdb; ipdb.set_trace()
        assert UpperBound_x >= LowerBound_x, "Error generating bounds. Not feasible!"
        FeasibleInput1 = (UpperBound_x-LowerBound_x)*np.random.rand() + LowerBound_x
        FeasibleInput2 = Constraint1/Coefficient2 - (Coefficient1/Coefficient2)*FeasibleInput1

    return(np.array([FeasibleInput1,FeasibleInput2],ndmin=1))

def run_sim_rand_TT(N,**kwargs):
    """
    Runs one simulation for MINIMUM ACTIVATION TRANSITION control.

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    **kwargs
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    1) Bounds - must be a (2,2) list with each row in ascending order. Default is given by Tension_Bounds.

    2) InitialAngularAcceleration - must be a float or an int. Default is 0 (starting from rest).

    3) thresh - must be an int. Default is 25.

    """
    thresh = kwargs.get("thresh",25)
    assert type(thresh)==int, "thresh should be an int as it is the number of attempts the program should run before stopping."

    AnotherIteration = True
    AttemptNumber = 1

    while AnotherIteration == True:
        X = np.zeros((2,N))
        X_o,InitialTensions = find_initial_values_TT(**kwargs)
        X[:,0] = X_o
        U = np.zeros((2,N))
        U[:,0] = InitialTensions.T

        AddNoise = False
        if AddNoise == True:
            np.random.seed(seed=None)
            NoiseArray = np.random.normal(loc=0.0,scale=0.2,size=(2,N))
        else:
            NoiseArray = np.zeros((2,N))

        try:
            cprint("Attempt #" + str(int(AttemptNumber)) + ":\n", 'green')
            statusbar = dsb(0,N-1,title=run_sim_rand_TT.__name__)
            for i in range(N-1):
            	U[:,i+1] = return_U_random_tensions(i,Time,X[:,i],U[:,i],Noise = NoiseArray[:,i])
            	X[:,i+1] = X[:,i] + dt*np.array([	dX1_dt(X[:,i]),\
            										dX2_dt(X[:,i],U=U[:,i+1])])
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
            	return(np.zeros((2,N)),np.zeros((2,N)))

def run_N_sim_rand_TT(**kwargs):
    NumberOfTrials = kwargs.get("NumberOfTrials",10)

    TotalX = np.zeros((NumberOfTrials,2,N))
    TotalU = np.zeros((NumberOfTrials,2,N))
    TerminalWidth = get_terminal_width()

    print("\n")
    for j in range(NumberOfTrials):
        TrialTitle = "          Trial #" + str(j+1)+ "          \n"
        print(
            " "*int(TerminalWidth/2 - len(TrialTitle)/2)
            + colored(TrialTitle,'white',attrs=["underline","bold"])
            )
        TotalX[j],TotalU[j] = run_sim_rand_TT(N,**kwargs)

    i=0
    NumberOfSuccessfulTrials = NumberOfTrials
    while i < NumberOfSuccessfulTrials:
        if (TotalX[i]==np.zeros((2,np.shape(TotalX)[2]))).all():
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

def plot_N_sim_rand_TT(t,TotalX,TotalU,**kwargs):
	Return = kwargs.get("Return",False)
	assert type(Return) == bool, "Return should either be True or False"

	fig1 = plt.figure(figsize = (9,7))
	fig1_title = "Underdetermined Forced-Pendulum Example"
	plt.title(fig1_title,fontsize=16,color='gray')
	statusbar = dsb(0,np.shape(TotalX)[0],title=(plot_N_sim_rand_TT.__name__ + " (" + fig1_title +")"))
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
	statusbar.reset(title=(plot_N_sim_rand_TT.__name__ + " (" + fig2_title +")"))
	for j in range(np.shape(TotalX)[0]):
		plt.plot(t, (r(t)-TotalX[j,0,:])*180/np.pi,color='0.70')
		statusbar.update(j)
	plt.xlabel("Time (s)")
	plt.ylabel("Error (Deg)")

	statusbar.reset(
		title=(
			plot_N_sim_rand_TT.__name__
			+ " (Plotting States, Inputs, and Muscle Length Comparisons)"
			)
		)
	for j in range(np.shape(TotalX)[0]):
		if j == 0:
			fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Tendon Tensions")
			fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Tendon Tensions")
		else:
			fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Tendon Tensions",\
									Figure=fig3)
			fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Tendon Tensions", \
									Figure = fig4)
		statusbar.update(j)
	if Return == True:
		return([fig1,fig2,fig3,fig4])
	else:
		plt.show()
