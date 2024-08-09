import numpy as np
import math
from sasdata.dataloader import data_info

# Constants (comments mostly copied from the original GSASIIsasd.py)
TEST_LIMIT        = 0.05                    # for convergence
CHI_SQR_LIMIT     = 0.01                    # maximum difference in ChiSqr for a solution
SEARCH_DIRECTIONS = 3                       # <10.  This code requires value = 3
RESET_STRAYS      = 1                       # was 0.001, correction of stray negative values
DISTANCE_LIMIT_FACTOR = 0.1                 # limitation on df to constrain runaways
MAX_MOVE_LOOPS = 5000                       # for no solution in routine: move (MaxEntMove)
MOVE_PASSES       = 0.001                   # convergence test in routine: move (MaxEntMove)

'''
sbmaxent

Entropy maximization routine as described in the article
J Skilling and RK Bryan; MNRAS 211 (1984) 111 - 124.
("MNRAS": "Monthly Notices of the Royal Astronomical Society")

:license: Copyright (c) 2013, UChicago Argonne, LLC
:license: This file is distributed subject to a Software License Agreement found
     in the file LICENSE that is included with this distribution. 

References:

1. J Skilling and RK Bryan; MON NOT R ASTR SOC 211 (1984) 111 - 124.
2. JA Potton, GJ Daniell, and BD Rainford; Proc. Workshop
   Neutron Scattering Data Analysis, Rutherford
   Appleton Laboratory, UK, 1986; ed. MW Johnson,
   IOP Conference Series 81 (1986) 81 - 86, Institute
   of Physics, Bristol, UK.
3. ID Culverwell and GP Clarke; Ibid. 87 - 96.
4. JA Potton, GK Daniell, & BD Rainford,
   J APPL CRYST 21 (1988) 663 - 668.
5. JA Potton, GJ Daniell, & BD Rainford,
   J APPL CRYST 21 (1988) 891 - 897.

'''
# All SB eq. refers to equations in the J Skilling and RK Bryan; MNRAS 211 (1984) 111 - 124. paper
# Overall idea is to maximize entropy S subject to constraint C<=C_aim, which is some Chi^2 target
# Most comments are copied from GSASIIsasd.py
# Currently, this code only works with spherical models

# Spherical form factor
def SphereFF(Q,Bins):
    QR = Q[:,np.newaxis]*Bins
    FF = (3./(QR**3))*(np.sin(QR)-(QR*np.cos(QR)))
    return FF

# Spherical volume
def SphereVol(Bins):
    Vol = (4./3.)*np.pi*Bins**3
    return Vol

class matrix_operation():
    # Transformation matrix
    def G_matrix(self, Q, Bins, contrast, choice, resolution):
        '''
        Defined as (form factor)^2 times volume times some scaling
        The integrand for Iq technically requires volume^2
        The size distribution obtained from this code takes care of the missing volume
        Therefore, it is IMPORTANT to not that the size distribution from this code is technically P(r) multiplied by something
        Converting to the size distribution back to P(r) isn't super straightforward and needs work (a TODO)
        '''
        Gmat = np.array([])
        # TODO: Make this G_matrix function flexible for other form factors (currerntly only works for spheres)
        # TODO: See if we can make use of existing Sasmodels
        if choice == 'Sphere':
            Gmat = 1.e-4*(contrast*SphereVol(Bins)*SphereFF(Q,Bins)**2).transpose()
        Gmat = resolution.apply(Gmat)
        Gmat = Gmat.reshape((len(Bins),len(Q)))
        return Gmat
    
    def matrix_transform(self, m1, m2):
        out = np.dot(m2,m1)
        return out
        

    def calculate_solution(self, data, G):
        # orginally named tropus in GSASIIsasd.py (comments also mostly from original code)
        '''
        Transform data-space -> solution-space:  [G] * data
        
        n = len(first_bins)
        npt = len(Iq) = len(Q)
        
        Definition according to SB: solution = image = a set of positive numbers which are to be determined and on which entropy is defined
        
        :param float[npt] data: related to distribution, ndarray of shape (npt)
        :param float[n][npt] G: transformation matrix, ndarray of shape (n,npt)
        :returns float[n]: calculated solution, ndarray of shape (n)
        '''
        solution = np.dot(G,data)
        return solution

    def calculate_data(self, solution, G):
        # orginally named opus in GSASIIsasd.py (comments also mostly from original code)
        '''
        Transform solution-space -> data-space:  [G]^tr * solution
        
        n = len(first_bins)
        npt = len(Iq) = len(Q)
        
        :param float[n] solution: related to Iq, ndarray of shape (n)
        :param float[n][npt] G: transformation matrix, ndarray of shape (n,npt)
        :returns float[npt]: calculated data, ndarray of shape (npt)
        '''
        data = np.dot(G.transpose(),solution)
        return data   

class decision_helper():
    class MaxEntException(Exception): 
        '''Any exception from this module'''
        pass

        #Dist, ChiNow, ChoSol, MaxEntMove, and MaxEnt_SB are all from GSASIIsasd.py
    def Dist(self, s2, beta):
        '''Measure the distance of this possible solution'''
        w = 0
        n = beta.shape[0]
        for k in range(n):
            z = -sum(s2[k] * beta)
            w += beta[k] * z
        return w

    def ChiNow(self, ax, c1, c2, s1, s2):
        '''
        ChiNow
        
        :returns tuple: (ChiNow computation of ``w``, beta)
        '''
        
        bx = 1 - ax
        a =   bx * c2  -  ax * s2
        b = -(bx * c1  -  ax * s1)

        beta = self.ChoSol(a, b)
        w = 1.0
        for k in range(SEARCH_DIRECTIONS):
            w += beta[k] * (c1[k] + 0.5*sum(c2[k] * beta))
        return w, beta

    def ChoSol(self, a, b):
        '''
        ChoSol: ? Chop the solution vectors ?
        
        :returns: new vector beta
        '''
        n = b.shape[0]
        fl = np.zeros((n,n))
        bl = np.zeros_like(b)
        
        if (a[0][0] <= 0):
            msg = "ChoSol: a[0][0] = " 
            msg += str(a[0][0])
            msg += '  Value must be positive'
            raise self.MaxEntException(msg)

        # first, compute fl from a
        # note fl is a lower triangular matrix
        fl[0][0] = math.sqrt (a[0][0])
        for i in (1, 2):
            fl[i][0] = a[i][0] / fl[0][0]
            for j in range(1, i+1):
                z = 0.0
                for k in range(j):
                    z += fl[i][k] * fl[j][k]
                z = a[i][j] - z
                if j == i:
                    y = math.sqrt(max(0.,z))
                else:
                    y = z / fl[j][j]
                fl[i][j] = y

        # next, compute bl from fl and b
        bl[0] = b[0] / fl[0][0]
        for i in (1, 2):
            z = 0.0
            for k in range(i):
                z += fl[i][k] * bl[k]
            bl[i] = (b[i] - z) / fl[i][i]

        # last, compute beta from bl and fl
        beta = np.empty((n))
        beta[-1] = bl[-1] / fl[-1][-1]
        for i in (1, 0):
            z = 0.0
            for k in range(i+1, n):
                z += fl[k][i] * beta[k]
            beta[i] = (bl[i] - z) / fl[i][i]

        return beta
class maxEntMethod():
    def MaxEntMove(self,fSum, blank, chisq, chizer, c1, c2, s1, s2):
        '''
        Goal is to choose the next target Chi^2
        And to move beta one step closer towards the solution (see SB eq. 12 and the text below for the definition of beta)
        '''
        helper = decision_helper()
        a_lower, a_upper = 0., 1.          # bracket  "a"
        cmin, beta = helper.ChiNow (a_lower, c1, c2, s1, s2)
        #print "MaxEntMove: cmin = %g" % cmin
        if cmin*chisq > chizer:
            ctarg = (1.0 + cmin)/2
        else:
            ctarg = chizer/chisq
        f_lower = cmin - ctarg
        c_upper, beta = helper.ChiNow (a_upper, c1, c2, s1, s2)
        f_upper = c_upper - ctarg

        fx = 2*MOVE_PASSES      # just to start off
        loop = 1
        while abs(fx) >= MOVE_PASSES and loop <= MAX_MOVE_LOOPS:
            a_new = (a_lower + a_upper) * 0.5           # search by bisection
            c_new, beta = helper.ChiNow (a_new, c1, c2, s1, s2)
            fx = c_new - ctarg
            # tighten the search range for the next pass
            if f_lower*fx > 0:
                a_lower, f_lower = a_new, fx
            if f_upper*fx > 0:
                a_upper, f_upper = a_new, fx
            loop += 1

        if abs(fx) >= MOVE_PASSES or loop > MAX_MOVE_LOOPS:
            msg = "MaxEntMove: Loop counter = " 
            msg += str(MAX_MOVE_LOOPS)
            msg += '  No convergence in alpha chop'
            raise helper.MaxEntException(msg)

        w = helper.Dist (s2, beta)
        m = SEARCH_DIRECTIONS
        if (w > DISTANCE_LIMIT_FACTOR*fSum/blank):        # invoke the distance penalty, SB eq. 17
            for k in range(m):
                beta[k] *= math.sqrt (fSum/(blank*w))
        chtarg = ctarg * chisq
        return w, chtarg, loop, a_new, fx, beta

    def MaxEnt_SB(self,Iq,sigma,Gqr,first_bins,IterMax=5000,report=True):
        '''
        Do the complete Maximum Entropy algorithm of Skilling and Bryan
        
        :param float Iq: background-subtracted scattering intensity data
        :param float sigma: normalization factor obtained using scale, weights, and weight factors
        :param float[][] G: transformation matrix
        :param float first_bins[]: initial guess for distribution
        :param int IterMax: maximum iterations allowed
        :param obj resolution: resolution object providing information about smearing
        :param boolean report: print report if True; do not print if False
        
        :returns float[]: :math:`f(r) dr`
        '''
        SEARCH_DIRECTIONS = 3
        CHI_SQR_LIMIT = 0.01
        n = len(first_bins)
        npt = len(Iq)
        
        operation = matrix_operation()
        
        xi = np.zeros((SEARCH_DIRECTIONS, n))
        eta = np.zeros((SEARCH_DIRECTIONS, npt))
        beta = np.zeros((SEARCH_DIRECTIONS))
        s2 = np.zeros((SEARCH_DIRECTIONS, SEARCH_DIRECTIONS))
        c2 = np.zeros((SEARCH_DIRECTIONS, SEARCH_DIRECTIONS))
        
        blank = sum(first_bins) / len(first_bins)            # average of initial bins before optimization
        chizer, chtarg = npt*1.0, npt*1.0
        f = first_bins * 1.0                                 # starting distribution is the same as the inital distribution
        fSum  = sum(f)                                       # find the sum of the f-vector
        z = (Iq - operation.matrix_transform(f, Gqr.transpose())) /sigma             # standardized residuals
        chisq = sum(z*z)                                     # Chi^2
        
        for iter in range(IterMax):
            ox = -2 * z / sigma                                    
            
            cgrad = operation.matrix_transform(ox, Gqr)  # cgrad[i] = del(C)/del(f[i]), SB eq. 8
            sgrad = -np.log(f/first_bins) / (blank*math.exp (1.0)) # sgrad[i] = del(S)/del(f[i])
            snorm = math.sqrt(sum(f * sgrad*sgrad))                # entropy, SB eq. 22
            cnorm = math.sqrt(sum(f * cgrad*cgrad))                # Chi^2, SB eq. 22
            tnorm = sum(f * sgrad * cgrad)                         # norm of gradient
            
            a = 1.0
            b = 1.0 / cnorm
            if iter == 0:
                test = 0.0     # mismatch between entropy and ChiSquared gradients
            else:
                test = math.sqrt( ( 1.0 - tnorm/(snorm*cnorm) )/2 ) # SB eq. 37?
                a = 0.5 / (snorm * test)
                b *= 0.5 / test
            xi[0] = f * cgrad / cnorm
            xi[1] = f * (a * sgrad - b * cgrad)
            
            eta[0] = operation.matrix_transform(xi[0], Gqr.transpose());          # solution --> data
            eta[1] = operation.matrix_transform(xi[1], Gqr.transpose());          # solution --> data
            ox = eta[1] / (sigma * sigma)
            xi[2] = operation.matrix_transform(ox, Gqr);          # data --> solution
            a = 1.0 / math.sqrt(sum(f * xi[2]*xi[2]))
            xi[2] = f * xi[2] * a
            eta[2] = operation.matrix_transform(xi[2], Gqr.transpose())           # solution --> data

            # prepare the search directions for the conjugate gradient technique
            c1 = xi.dot(cgrad) / chisq                          # C_mu, SB eq. 24
            s1 = xi.dot(sgrad)                                  # S_mu, SB eq. 24

            
            for k in range(SEARCH_DIRECTIONS):
                for l in range(k+1):
                    c2[k][l] = 2 * sum(eta[k] * eta[l] / sigma/sigma) / chisq
                    s2[k][l] = -sum(xi[k] * xi[l] / f) / blank

            # reflect across the body diagonal
            for k, l in ((0,1), (0,2), (1,2)):
                c2[k][l] = c2[l][k]                     #  M_(mu,nu)
                s2[k][l] = s2[l][k]                     #  g_(mu,nu)
    
            beta[0] = -0.5 * c1[0] / c2[0][0]
            beta[1] = 0.0
            beta[2] = 0.0
            if (iter > 0):
                w, chtarg, loop, a_new, fx, beta = self.MaxEntMove(fSum, blank, chisq, chizer, c1, c2, s1, s2)
                
            f_old = f.copy()                # preserve the last solution
            f += xi.transpose().dot(beta)   # move the solution towards the solution, SB eq. 25
        
            # As mentioned at the top of p.119,
            # need to protect against stray negative values.
            # In this case, set them to RESET_STRAYS * base[i]
            #f = f.clip(RESET_STRAYS * blank, f.max())
            for i in range(n):
                if f[i] <= 0.0:
                    f[i] = RESET_STRAYS * first_bins[i]
            df = f - f_old
            fSum = sum(f)
            fChange = sum(df)

            # calculate the normalized entropy
            S = sum((f/fSum) * np.log(f/fSum))                     # normalized entropy, S&B eq. 1
            z = (Iq - operation.matrix_transform(f, Gqr.transpose())) / sigma              # standardized residuals
            chisq = sum(z*z)                                       # report this ChiSq

            if report:
                print (" MaxEnt trial/max: %3d/%3d" % ((iter+1), IterMax))
                print (" Residual: %5.2lf%% Entropy: %8lg" % (100*test, S))
                print (" Function sum: %.6lg Change from last: %.2lf%%\n" % (fSum,100*fChange/fSum))
                
            # See if we have finished our task.
            # do the hardest test first
            if (abs(chisq/chizer-1.0) < CHI_SQR_LIMIT) and  (test < TEST_LIMIT):
                print (' Convergence achieved.')
                return chisq,f,operation.matrix_transform(f, Gqr.transpose())     # solution FOUND returns here
        print (' No convergence! Try increasing Error multiplier.')
        return chisq,f,operation.matrix_transform(f, Gqr.transpose())             # no solution after IterMax iterations

def sizeDistribution(input):
    '''
    :param dict input:
        input must have the following keys, each corresponding to their specified type of values:
        Key                          | Value
        __________________________________________________________________________________________
        Data                         | list[float[npt],float[npt]]: I and Q. The two arrays should both be length npt
        Limits                       | float[2]: a length-2 array contains Qmin and Qmax
        Scale                        | float:
        DiamRange                    | float[3]: A length-3 array contains minimum and maximum diameters between which the 
                                                 distribution will be constructed, and the thid number is the number of bins 
                                                 (must be an integer) (TODO: maybe restructure that)
        LogBin                       | boolean: Bins will be on a log scale if True; bins will be on a linear scale is False 
        WeightFactors                | float[npt]: Factors on the weights
        Contrast                     | float: The difference in SLD between the two phases
        Sky                          | float: Should be small but non-zero (TODO: Check this statement)
        Weights                      | float[npt]: Provide some sort of uncertainty. Examples include dI and 1/I
        Background                   | float[npt]: Scattering background to be subtracted
        Resolution                   | obj: resolution object
        Model                        | string: model name, currently only supports 'Sphere'
    '''
    iterMax = input["IterMax"]      
    Qmin = input["Limits"][0]
    Qmax = input["Limits"][1]
    scale = input["Scale"]
    minDiam = input["DiamRange"][0]
    maxDiam = input["DiamRange"][1]
    Nbins = input["DiamRange"][2]
    Q,I = input["Data"]
    if input["Logbin"]:
        Bins = np.logspace(np.log10(minDiam),np.log10(maxDiam),Nbins+1,True)/2        #make radii
    else:
        Bins = np.linspace(minDiam,maxDiam,Nbins+1,True)/2        #make radii
    Dbins = np.diff(Bins)
    Bins = Bins[:-1]+Dbins/2.
    Ibeg = np.searchsorted(Q,Qmin)
    Ifin = np.searchsorted(Q,Qmax)+1        #include last point
    wtFactor = input["WeightFactors"][Ibeg:Ifin]
    BinMag = np.zeros_like(Bins)
    contrast = input["Contrast"]
    Ic = np.zeros(len(I))
    sky = input["Sky"]
    wt = input["Weights"][Ibeg:Ifin]
    Back = input["Background"][Ibeg:Ifin]
    res = input["Resolution"]
    Gmat = matrix_operation().G_matrix(Q[Ibeg:Ifin],Bins,contrast,input["Model"],res)
    BinsBack = np.ones_like(Bins)*sky*scale/contrast
    MethodCall = maxEntMethod()
    chisq,BinMag,Ic[Ibeg:Ifin] = MethodCall.MaxEnt_SB(scale*I[Ibeg:Ifin]-Back,scale/np.sqrt(wtFactor*wt),Gmat,BinsBack,iterMax,report=True)
    BinMag = BinMag/(2.*Dbins)
    return chisq,Bins,Dbins,BinMag,Q[Ibeg:Ifin],Ic[Ibeg:Ifin]