""" Tiny pure-python implementation of Microsoft's TrueSkill
    algorithm, only for 1-on-1 matches. TrueSkill is ELO with 
    adjustments for uncertainty of skill level.
"""

__author__ = "Thomas van den Berg"

### Imports ###
from math import *


### Constants ###

INITIAL_MU    = 100
INITIAL_SIGMA = INITIAL_MU / 2.0
BETA          = INITIAL_SIGMA / 5.0
GAMMA         = INITIAL_SIGMA / 100.0
EPSILON       = 5.0 #icdf((1.1)/2) * sqrt(2) * BETA
DRAW_MARGIN   = 0.05

### Functions ###

def erfcc(x):
    """ Complementary error function.
        From http://stackoverflow.com/a/809402/224949.
    """
    z = abs(x)
    t = 1. / (1. + 0.5*z)
    r = t * exp(-z*z-1.26551223+t*(1.00002368+t*(.37409196+
        t*(.09678418+t*(-.18628806+t*(.27886807+
        t*(-1.13520398+t*(1.48851587+t*(-.82215223+
        t*.17087277)))))))))
    if (x >= 0.):
        return r
    else:
        return 2. - r

def pdf(x):
    return exp(-x**2/2)/sqrt(2*pi)

def cdf(x):
    return 1. - 0.5*erfcc(x/(2**0.5))

# Functions below are from
# https://github.com/dougz/trueskill

def v_win(t, e):
    """Updates score"""
    return pdf(t-e) / cdf(t-e)
  
def w_win(t, e):
    """Updates sigma"""
    return v_win(t, e) * (v_win(t, e) + t - e)

def v_draw(t, e):
    return (pdf(-e-t) - pdf(e-t)) / (cdf(e-t) - cdf(-e-t))
  
def w_draw(t, e):
    return v_draw(t, e) ** 2 + ((e-t) * pdf(e-t) + (e+t) * pdf(e+t)) / (cdf(e-t) - cdf(-e-t))
  

def adjust((mu_w, sig_w), (mu_l, sig_l), draw=False, beta=BETA, epsilon=EPSILON, gamma=GAMMA):
    """ Implements the 2-player skill update as described on
        http://research.microsoft.com/en-us/projects/trueskill/details.aspx#update
    """
    c = sqrt(2*beta**2 + sig_w + sig_l)
    e = epsilon/c
    if draw:
        v = v_draw
        w = w_draw
    else:
        v = v_win
        w = w_win
    new_mu_w = mu_w + (sig_w / c) * v((mu_w-mu_l)/c, e)
    new_mu_l = mu_l - (sig_l / c) * v((mu_w-mu_l)/c, e)
    new_sig_w = gamma + sig_w * (1 - (sig_w / (c*c)) * w((mu_w-mu_l)/c, e))
    new_sig_l = gamma + sig_l * (1 - (sig_l / (c*c)) * w((mu_w-mu_l)/c, e))
    
    return (new_mu_w, new_sig_w), (new_mu_l, new_sig_l)
    
    
if __name__ == "__main__":
    a = (70.2, 29.4)
    b = ( 70.2, 26.1 )
    
    
    (a, b) = adjust(a, b)
    print a,b
    (a, b) = adjust(a, b)
    print a,b
    (a, b) = adjust(a, b)
    print a,b
    (a, b) = adjust(a, b)
    print a,b
