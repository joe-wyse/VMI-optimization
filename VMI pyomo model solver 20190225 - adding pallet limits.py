# -*- coding: utf-8 -*-
"""
Created on Thu Feb 21 20:36:17 2019

@author: JWeiz

VMI Pyomo model. Includes pallets inbound, layers inbound, total inbound, and
ending balance on hand. 

Includes cost for picks

"""
from pyomo.environ import *
model = ConcreteModel()

cutcost = 10
overagecost = 1
pickcost = 1


skulist = ['D6CSPIN','D1214SW']
dclist = ['Salem','Memphis']


dates = [0,1,2,3,4]


demandtab = {
    (0,'Salem','D6CSPIN')   : 119,   
    (1,'Salem','D6CSPIN')   : 189,
    (2,'Salem','D6CSPIN')   : 133,
    (3,'Salem','D6CSPIN')   : 159,
    (4,'Salem','D6CSPIN')   : 181,
    (0,'Salem','D1214SW')   : 177,
    (1,'Salem','D1214SW')  : 121,
    (2,'Salem','D1214SW')   : 155,
    (3,'Salem','D1214SW')   : 90,
    (4,'Salem','D1214SW')   : 122,
    (0,'Memphis','D6CSPIN')   : 190,   
    (1,'Memphis','D6CSPIN')   : 120,
    (2,'Memphis','D6CSPIN')   : 222,
    (3,'Memphis','D6CSPIN')   : 125,
    (4,'Memphis','D6CSPIN')   : 18,
    (0,'Memphis','D1214SW')   : 44,
    (1,'Memphis','D1214SW')  : 250,
    (2,'Memphis','D1214SW')   : 255,
    (3,'Memphis','D1214SW')   : 355,
    (4,'Memphis','D1214SW')   : 150,
    }

#Solver currently can't handle extreme production shortages
#it doesn't know how to portion out limited product to the different DC's
#I need to make cuts cost increase as number of cuts increases
#I should also assign this cost per DC, so that we can favor some DC's over others
#I should probably also assign different overage costs per DC 
max_by_sku_tab = {
    (0,'D6CSPIN')   : 1000,   
    (1,'D6CSPIN')   : 1000,
    (2,'D6CSPIN')   : 1000,
    (3,'D6CSPIN')   : 1000,
    (4,'D6CSPIN')   : 0,
    (0,'D1214SW')   : 1300,
    (1,'D1214SW')   : 1300,
    (2,'D1214SW')   : 1300,
    (3,'D1214SW')   : 1000,
    (4,'D1214SW')   : 1300,
    }

max_pallets_tab = {
        (0,'Salem') : 30,
        (1,'Salem') : 30,
        (2,'Salem') : 30,
        (3,'Salem') : 30,
        (4,'Salem') : 22,
        (0,'Memphis') : 30,
        (4,'Memphis') : 30,
        (1,'Memphis') : 30,
        (2,'Memphis') : 30,
        (3,'Memphis') : 0,
        }

min_pallets_tab = {
        (0,'Salem') : 0,
        (1,'Salem') : 0,
        (2,'Salem') : 0,
        (3,'Salem') : 0,
        (4,'Salem') : 0,
        (0,'Memphis') : 0,
        (1,'Memphis') : 0,
        (2,'Memphis') : 0,
        (3,'Memphis') : 0,
        (4,'Memphis') : 0,
        }



pallettab = {
        ('D6CSPIN') : 130,
        ('D1214SW') : 190,
        }

layertab = {
        ('D6CSPIN') : 10,
        ('D1214SW') : 10,
        }

#This will eventually be an import from an Excel sheet
bbohtab = {
    ('Salem','D6CSPIN')   : 5,   
    ('Salem','D1214SW')   : 14,
    ('Memphis','D6CSPIN')   : 19,   
    ('Memphis','D1214SW')   : 44,
    }


model.dates = Set(initialize=dates)
model.skus = Set(initialize=skulist)
model.dcs = Set(initialize=dclist)
model.demand = Param(model.dates, model.dcs, model.skus, initialize = demandtab)
model.palsize = Param(model.skus, initialize = pallettab)
model.layersize = Param(model.skus, initialize = layertab)
model.max_by_item = Param(model.dates, model.skus, initialize = max_by_sku_tab)
model.max_pallets = Param(model.dates, model.dcs, initialize = max_pallets_tab)
model.min_pallets = Param(model.dates, model.dcs, initialize = min_pallets_tab)
model.bboh = Var(model.dates, model.dcs, model.skus, initialize=0)
model.eboh = Var(model.dates, model.dcs, model.skus, initialize=0)
model.inbound_layers = Var(model.dates, model.dcs, model.skus, domain = NonNegativeIntegers)
model.inbound_pallets = Var(model.dates, model.dcs, model.skus, domain = NonNegativeIntegers)
model.total_inbound = Var(model.dates, model.dcs, model.skus, domain = NonNegativeIntegers)
model.inventory_cost = Var(model.dates, model.dcs, model.skus,domain=NonNegativeReals)
model.picks_cost = Var(model.dates, model.dcs, model.skus,domain=NonNegativeReals)
model.total_cost = Var(model.dates, model.dcs, model.skus,domain=NonNegativeReals)
model.total_pallets = Var(model.dates, model.dcs, model.skus, domain = NonNegativeReals)


#eventually, use the initial date instead of 0
def bboh_rule(model,date,dc,sku):
    if date == 0:
        return model.bboh[date,dc,sku] == bbohtab[dc,sku]
    elif date >=1:
        if value(model.eboh[date-1,dc,sku]) >= 0:
            return model.bboh[date,dc,sku] == model.eboh[date-1,dc,sku]
        else:
            model.bboh[date,dc,sku] == 0
model.bboh_rule = Constraint(model.dates, model.dcs, model.skus, rule = bboh_rule)


def eboh_rule(model,date,dc,sku):
    return model.eboh[date,dc,sku] == model.bboh[date,dc,sku] \
    + model.total_inbound[date,dc,sku] - model.demand[date,dc,sku]
model.eboh_rule = Constraint(model.dates,model.dcs, model.skus, rule = eboh_rule)

#total cases sent
def total_inbound_rule(model, date, dc, sku):
    return model.total_inbound[date,dc,sku] == model.inbound_pallets[date,dc,sku]*model.palsize[sku] \
+ model.inbound_layers[date,dc,sku]*model.layersize[sku]
model.total_inbound_rule = Constraint(model.dates, model.dcs, model.skus, rule = total_inbound_rule)

#total pallets sent (includes layers, used for truck utilization)
#this will need adjusting because picks add up to more than the sum of their parts
def total_pallets_rule(model, date, dc, sku):
    return model.total_pallets[date, dc, sku] == model.total_inbound[date, dc, sku]/model.palsize[sku]
model.total_pallets_rule = Constraint(model.dates, model.dcs, model.skus, rule = total_pallets_rule)


def max_by_dc_rule(model, date, dc):
    return sum(model.total_pallets[date, dc, sku] for sku in model.skus) <= model.max_pallets[date, dc]
model.max_by_dc = Constraint(model.dates, model.dcs, rule = max_by_dc_rule)


def min_by_dc_rule(model, date, dc):
    return sum(model.total_pallets[date, dc, sku] for sku in model.skus) >= model.min_pallets[date, dc]
model.min_by_dc = Constraint(model.dates, model.dcs, rule = min_by_dc_rule)


def max_by_sku_rule(model, date, sku):
    return sum(model.total_inbound[date, dc, sku] for dc in model.dcs) <= model.max_by_item[date, sku]
model.max_by_sku = Constraint(model.dates, model.skus, rule = max_by_sku_rule)




'''
def max_pallets_per_dc_rule(model, date, dc):
    return sum(model.total_inbound[date, dc, sku]/model.palsize[sku] for sku in model.skus) <= model.max_pallets(date, dc)
model.max_pallets_per_dc_rule = Constraint(model.dates, model.dcs, rule = max_pallets_per_dc_rule)
'''

#Add cost of picks in here somehow
def inventory_cost_rule(model,date,dc,sku):
    if value(model.eboh[date,dc,sku]) >= 0:
        return model.inventory_cost[date,dc,sku] == model.eboh[date,dc,sku]*overagecost
    else:
        return model.inventory_cost[date,dc,sku] == -(model.eboh[date,dc,sku]*cutcost)
model.inventory_cost_rule = Constraint(model.dates,model.dcs,model.skus,rule=inventory_cost_rule)

#picks cost
def picks_cost_rule(model,date,dc,sku):
    return model.picks_cost[date, dc, sku] == model.inbound_layers[date, dc, sku] * model.layersize[sku] * pickcost
    
model.picks_cost_rule = Constraint(model.dates,model.dcs,model.skus,rule=picks_cost_rule)

#total cost equals inventory cost plus picks cost
def total_cost_rule(model,date,dc,sku):
    return model.total_cost[date, dc, sku] == model.inventory_cost[date, dc, sku] \
+ model.picks_cost[date, dc, sku]
model.total_cost_rule = Constraint(model.dates,model.dcs,model.skus,rule=total_cost_rule)


def obj_rule(model):
    return sum(model.total_cost[date,dc,sku] for date in model.dates for dc in model.dcs for sku in model.skus)
model.objective = Objective(rule = obj_rule, sense = minimize)


## Display the output ##
def pyomo_postprocess(options=None, instance=None, results=None):
  model.inbound_pallets.display()
  model.inbound_layers.display()
  model.total_inbound.display()
  model.demand.display()  
  model.bboh.display()
  model.eboh.display()
  
  

# This is an optional code path that allows the script to be run outside of
# pyomo command-line.  For example:  python transport.py
if __name__ == '__main__':
    # This emulates what the pyomo command-line tools does
    from pyomo.opt import SolverFactory
    import pyomo.environ
    opt = SolverFactory("glpk")
    results = opt.solve(model)
    #sends results to stdout
    results.write()
    print("\nDisplaying Solution\n" + '-'*60)
    pyomo_postprocess(None, model, results)
