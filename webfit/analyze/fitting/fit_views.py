import json
from logging import getLogger

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser

from bumps.names import *
from bumps.bounds import Bounded
from sasmodels.core import load_model, load_model_info
from sasmodels.data import load_data
from sasmodels.bumps_model import Model, Experiment
from sasdata.dataloader.loader import Loader
from sas.sascalc.fit.models import ModelManager
from bumps import fitters
from bumps.formatnum import format_uncertainty
#TODO categoryinstallers should belong in SasView.Systen rather than in QTGUI
from sas.qtgui.Utilities.CategoryInstaller import CategoryInstaller

from serializers import (
    FitSerializer,
    FitParameterSerializer,
)
from data.models import Data
from .models import (
    Fit,
    FitParameter,
)


fit_logger = getLogger(__name__)
model_manager = ModelManager()
MODEL_CHOICES = model_manager.get_model_list

#start() only puts all the request data into the db, start_fit() runs calculations
@api_view(["PUT"])
def start(request, version = None):
    base_serializer = FitSerializer(is_public = request.data.is_public)
    
    #TODO WIP not sure if this works yet
    if request.method == "PUT":
        #set status

        #try to create model for check if the modelstring is valid
        if load_model(request.data.model):
            curr_model = request.data.model
            base_serializer(model = curr_model)
            #would return a dictionary
            default_parameters = load_model_info(curr_model).parameters.defaults

        else:
            return HttpResponseBadRequest("No model selected for fitting")

        if request.data.data_id:
            if Data.objects.filter(is_public = True, id = request.data.data_id).get():
                return HttpResponseBadRequest("data isn't public")
            if not (request.user.is_authenticated and 
                    request.user is Data.objects.get(id=request.data.data_id).current_user):
                return HttpResponseBadRequest("data is not user's")
            #search online to see how to add serializers.PrimaryKeyRelatedField
            base_serializer(data_id = request.data.data_id)

        if request.data.parameters:
            parameters = JSONParser().parse(request.data.parameters)
            all_param_dbs = []
            for value in parameters:
                parameter_serializer = FitParameterSerializer(base_id = base_serializer.data.id, data = value)
                if parameter_serializer.is_valid():
                    parameter_serializer.save()
                all_param_dbs.append(get_object_or_404(FitParameter, base_id = parameter_serializer.data.base_id, name = parameter_serializer.data.name))
            #{str: name, value}
            pars = {}
            for x in all_param_dbs:
                num = eval(f"{x.datatype}({x.value})")
                #TODO check if x.name is a valid parameter else return blah
                #pars = {x.name: num for x in parameter_serializer.data for num = eval(...)}
                pars[x.name] = num
                        #check with default list
            for key, value in default_parameters.items():
                if key not in pars.keys():
                    pars[key] = value

        if base_serializer.is_valid():
            base_serializer.save()
        else:
            return HttpResponseBadRequest("Serializer error")

        #start_fit(curr_model, base_serializer.data, pars, parameters)
        #add "warnings": ... later
        return {"authenticated":request.user.is_authenticated, "fit_id":base_serializer.data.id}
    return HttpResponseBadRequest()


def start_fit(model, data = None, params = None, param_limits = None):
    if params is None:
        params = load_model_info(model).parameters.defaults

    current_model = load_model(model)
    model = Model(current_model, **params)
    model.radius.range(1, 50)
    model.length.range(1, 500)
    #rewrite to figure out if they can pass only one upper/lower
    """if params is None and param_limits is None:
        model.radius.range(Bounded.limits)
        model.length.range(Bounded.limits)
    else:
        if param_limits.radius.lower_limit:
            model.radius.range(param_limits.radius.lower_limit, param_limits.radius.upper_limit)
        if param_limits.radius.upper_limit:
            
        if param_limits.length.lower_limit or param_limits.length.upper_limit:
            model.length.range(param_limits.length.lower_limit, param_limits.length.upper_limit)"""
    loader = Loader()
    if data is None:
        f = get_object_or_404(Data, is_public = True).file
        test_data = load_data(f.path)
        M = Experiment(data = test_data, model = model)
    else:
        f = get_object_or_404(Data, id = data.id).file
        test_data = load_data(f.path)
        test_data.dy = 0.2*test_data.y
        M = Experiment(data = test_data, model=model)
    problem = FitProblem(M)
    result = fit(problem, method='amoeba')
    #problem.fitness.model.state() <- return this dictionary to check if fit is actually working
    return result


def status():
    return 0


@api_view(["GET"])
def fit_status(request, fit_id, version = None):
    fit_obj = get_object_or_404(Fit, id = fit_id)
    if request.method == "GET":
        #TODO figure out private later <- probs write in Fit model
        if not (fit_obj.is_public or request.user.is_authenticated):
            return HttpResponseBadRequest("user isn't logged in")
        return_info = {"fit_id" : fit_id, "status" : Fit.status}
        if Fit.results:
            return_info+={"results" : Fit.results}
        return return_info
    return HttpResponseBadRequest()


@api_view(["GET"])
def list_optimizers(request, version = None):
    if request.method == "GET":
        return_info = {"optimizers" : [fitters.FIT_ACTIVE_IDS]}
        return return_info
    return HttpResponseBadRequest()


@api_view(["GET"])
def list_models(request, version = None):
    if request.method == "GET":
        unique_models = {"models": []}
        if request.categories:
            user_file = CategoryInstaller.get_user_file()
            with open(user_file) as cat_file:
                file_contents = cat_file.read()
            spec_cat = file_contents[request.data.categories]
            unique_models["models"] += [spec_cat]
        #elif: request.kind
        else:
            unique_models["models"] = [MODEL_CHOICES]
        return unique_models
        """TODO requires discussion:
        if request.username:
            if request.user.is_authenticated:
                user_models = 
                listed_models += {"plugin_models": user_models}
        """
    return HttpResponseBadRequest()

#takes DataInfo and saves it into to specified file location
