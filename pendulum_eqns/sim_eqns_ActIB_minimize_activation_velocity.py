import numpy as np
import matplotlib.pyplot as plt
from termcolor import cprint,colored
from danpy.sb import dsb,get_terminal_width
from pendulum_eqns.init_muscle_activation_controlled_model import *

N_seconds = 1
N = N_seconds*10000 + 1
Time = np.linspace(0,N_seconds,N)
dt = Time[1]-Time[0]

def return_U_muscle_activation_nearest_neighbor(i,t,X,U,**kwargs):
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

	dt = t[1]-t[0]

	Noise = kwargs.get("Noise",np.zeros((2,)))
	assert np.shape(Noise) == (2,) and str(type(Noise)) == "<class 'numpy.ndarray'>", "Noise must be a (2,) numpy.ndarray"

	Seed = kwargs.get("Seed",None)
	assert type(Seed) in [float,int] or Seed is None, "Seed must be a float or an int or None."
	np.random.seed(Seed)

	Bounds = kwargs.get("Bounds",Activation_Bounds)
	assert type(Bounds) == list and np.shape(Bounds) == (2,2), "Bounds for Muscle Activation Control must be a (2,2) list."
	assert Bounds[0][0]<Bounds[0][1],"Each set of bounds must be in ascending order."
	assert Bounds[1][0]<Bounds[1][1],"Each set of bounds must be in ascending order."

	Coefficient1,Coefficient2,Constraint1 = return_constraint_variables(t[i],X)
	assert Coefficient1!=0 and Coefficient2!=0, "Error with Coefficients. Shouldn't both be zero."
	if Constraint1 < 0:
		assert not(Coefficient1 > 0 and Coefficient2 > 0), "Infeasible activations. (Constraint1 < 0, Coefficient1 > 0, Coefficient2 > 0)"
	if Constraint1 > 0:
		assert not(Coefficient1 < 0 and Coefficient2 < 0), "Infeasible activations. (Constraint1 > 0, Coefficient1 < 0, Coefficient2 < 0)"

	if Coefficient1 == 0:
		LowerBound_x = max(Bounds[0][0],AllowbaleBounds_x[0])
		UpperBound_x = min(Bounds[0][1],AllowbaleBounds_x[1])
		FeasibleInput1 = (UpperBound_x-LowerBound_x)*np.random.rand(1000) + LowerBound_x
		FeasibleInput2 = np.array([Constraint1/Coefficient2]*1000)
	elif Coefficient2 == 0:
		LowerBound_y = max(Bounds[1][0],AllowableBounds_y[0])
		UpperBound_y = min(Bounds[1][1],AllowableBounds_y[1])
		FeasibleInput1 = np.array([Constraint1/Coefficient1]*1000)
		FeasibleInput2 = (UpperBound_y-LowerBound_y)*np.random.rand(1000) + LowerBound_y
	else:
		SortedBounds = np.sort([(Constraint1-Coefficient2*Bounds[1][0])/Coefficient1,\
									(Constraint1-Coefficient2*Bounds[1][1])/Coefficient1])
		LowerBound_x = max(	Bounds[0][0],\
		 					SortedBounds[0]\
						)
		UpperBound_x = min(	Bounds[0][1],\
		 					SortedBounds[1]\
						)
		# if UpperBound_x < LowerBound_x: import ipdb; ipdb.set_trace()
		assert UpperBound_x >= LowerBound_x, "Error generating bounds. Not feasible!"
		# FeasibleInput1 = (UpperBound_x-LowerBound_x)*np.random.rand(1000) + LowerBound_x
		# FeasibleInput2 = np.array([Constraint1/Coefficient2 - (Coefficient1/Coefficient2)*el \
		# 						for el in FeasibleInput1])
		FeasibleInput1 = np.ones(1000)*(Coefficient2*(Coefficient2*U[0]-Coefficient1*U[1])+Coefficient1*Constraint1)/(Coefficient1**2 + Coefficient2**2)
		FeasibleInput2 = np.ones(1000)*(Coefficient1*(-Coefficient2*U[0]+Coefficient1*U[1])+Coefficient2*Constraint1)/(Coefficient1**2 + Coefficient2**2)
		assert LowerBound_x<=FeasibleInput1[0]<=UpperBound_x, "No Feasible transition. Closest transition greater than maximum allowable transition."
	"""
	Checking to see which inputs have the appropriate allowable step size.
	"""
	# euclid_dist = np.array(list(map(lambda x,y: np.sqrt((U[0]-x)**2+(U[1]-y)**2),\
	# 								FeasibleInput1,FeasibleInput2)))
	# next_index, = np.where(euclid_dist==min(euclid_dist))
	# u1 = FeasibleInput1[next_index[0]]
	# u2 = FeasibleInput2[next_index[0]]
	u1 = FeasibleInput1[0]
	u2 = FeasibleInput2[0]
	return(np.array([u1,u2]))

def run_sim_MAV(**kwargs):
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
			statusbar = dsb(0,N-1,title=run_sim_MAV.__name__)
			for i in range(N-1):
				U[:,i+1] = return_U_muscle_activation_nearest_neighbor(i,Time,X[:,i],U[:,i],Noise = NoiseArray[:,i])
				X[:,i+1] = X[:,i] + dt*np.array([	dX1_dt(X[:,i]),\
													dX2_dt(X[:,i]),\
													dX3_dt(X[:,i]),\
													dX4_dt(X[:,i]),\
													dX5_dt(X[:,i]),\
													dX6_dt(X[:,i]),\
													dX7_dt(X[:,i],U=U[:,i+1]),\
													dX8_dt(X[:,i],U=U[:,i+1])])
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

def run_N_sim_MAV(**kwargs):
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
		TotalX[j],TotalU[j] = run_sim_MAV(**kwargs)

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

def plot_N_sim_MAV(t,TotalX,TotalU,**kwargs):
	Return = kwargs.get("Return",False)
	assert type(Return) == bool, "Return should either be True or False"

	fig1 = plt.figure(figsize = (9,7))
	fig1_title = "Underdetermined Forced-Pendulum Example"
	plt.title(fig1_title,fontsize=16,color='gray')
	statusbar = dsb(0,np.shape(TotalX)[0],title=(plot_N_sim_MAV.__name__ + " (" + fig1_title +")"))
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
	statusbar.reset(title=(plot_N_sim_MAV.__name__ + " (" + fig2_title +")"))
	for j in range(np.shape(TotalX)[0]):
		plt.plot(t, (r(t)-TotalX[j,0,:])*180/np.pi,color='0.70')
		statusbar.update(j)
	plt.xlabel("Time (s)")
	plt.ylabel("Error (Deg)")

	statusbar.reset(
		title=(
			plot_N_sim_MAV.__name__
			+ " (Plotting States, Inputs, and Muscle Length Comparisons)"
			)
		)
	for j in range(np.shape(TotalX)[0]):
		if j == 0:
			fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Muscle Activations")
			fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Muscle Activations")
			fig5 = plot_l_m_comparison(t,TotalX[j],MuscleLengths = TotalX[j,4:6,:],Return=True,InputString = "Muscle Activation")
		else:
			fig3 = plot_states(t,TotalX[j],Return=True,InputString = "Muscle Activations",\
									Figure=fig3)
			fig4 = plot_inputs(t,TotalU[j],Return=True,InputString = "Muscle Activations", \
									Figure = fig4)
			fig5 = plot_l_m_comparison(t,TotalX[j],MuscleLengths = TotalX[j,4:6,:],Return=True,\
											InputString = "Muscle Activation", Figure = fig5)
		statusbar.update(j)
	if Return == True:
		return([fig1,fig2,fig3,fig4,fig5])
	else:
		plt.show()
