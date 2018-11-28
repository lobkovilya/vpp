#!/usr/bin/env python2
#
# Copyright (c) 2016,2018 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from string import Template

from jvpp_model import is_control_ping, is_control_ping_reply, is_dump, is_request, is_details, is_reply, is_event


def generate_future_facade(work_dir, model, logger):
    logger.debug("Generating JVpp future facade for %s" % model.json_api_files)
    _generate_future_jvpp(work_dir, model),
    _generate_future_jvpp_facade(work_dir, model)
    _generate_future_jvpp_callback(work_dir, model)


def _generate_future_jvpp(work_dir, model):
    with open("%s/FutureJVpp%s.java" % (work_dir, model.plugin_java_name), "w") as f:
        f.write(_FUTURE_JVPP_TEMPLATE.substitute(
            plugin_package=model.plugin_package,
            json_filename=model.json_api_files,
            plugin_name=model.plugin_java_name,
            methods=_generate_future_jvpp_methods(model)
        ))

_FUTURE_JVPP_TEMPLATE = Template('''
package $plugin_package.future;

/**
 * <p>Async facade extension adding specific methods for each request invocation
 * <br>It was generated by jvpp_future_facade_gen.py based on $json_filename.
 */
public interface FutureJVpp${plugin_name} extends io.fd.vpp.jvpp.future.FutureJVppInvoker {
$methods

    @Override
    public $plugin_package.notification.${plugin_name}EventRegistry getEventRegistry();

}
''')


def _generate_future_jvpp_methods(model):
    methods = []
    for msg in model.messages:
        if is_control_ping(msg) or is_control_ping_reply(msg):
            # Skip control_ping managed by jvpp registry.
            continue
        reply_name = None
        if is_request(msg):
            reply_name = msg.reply_java
        elif is_dump(msg):
            # use reply dump wrappers
            reply_name = "%sReplyDump" % msg.reply_java
        else:
            continue

        methods.append(_FUTURE_JVPP_METHOD_TEMPLATE.substitute(
            plugin_package=model.plugin_package,
            method_name=msg.java_name_lower,
            reply_name=reply_name,
            request_name=msg.java_name_upper
        ))
    return "".join(methods)

_FUTURE_JVPP_METHOD_TEMPLATE = Template('''
    java.util.concurrent.CompletionStage<${plugin_package}.dto.${reply_name}> ${method_name}(${plugin_package}.dto.${request_name} request);
''')


def _generate_future_jvpp_facade(work_dir, model):
    with open("%s/FutureJVpp%sFacade.java" % (work_dir, model.plugin_java_name), "w") as f:
        f.write(_FUTURE_JVPP_FACADE_TEMPLATE.substitute(
            plugin_package=model.plugin_package,
            json_filename=model.json_api_files,
            plugin_name=model.plugin_java_name,
            methods=_generate_future_jvpp_facade_methods(model)
        ))

_FUTURE_JVPP_FACADE_TEMPLATE = Template('''
package $plugin_package.future;

/**
 * <p>Implementation of FutureJVpp based on AbstractFutureJVppInvoker
 * <br>It was generated by jvpp_future_facade_gen.py based on $json_filename.
 */
public class FutureJVpp${plugin_name}Facade extends io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker implements FutureJVpp${plugin_name} {

    private final $plugin_package.notification.${plugin_name}EventRegistryImpl eventRegistry = new $plugin_package.notification.${plugin_name}EventRegistryImpl();

    /**
     * <p>Create FutureJVpp${plugin_name}Facade object for provided JVpp instance.
     * Constructor internally creates FutureJVppFacadeCallback class for processing callbacks
     * and then connects to provided JVpp instance
     *
     * @param jvpp provided io.fd.vpp.jvpp.JVpp instance
     *
     * @throws java.io.IOException in case instance cannot connect to JVPP
     */
    public FutureJVpp${plugin_name}Facade(final io.fd.vpp.jvpp.JVppRegistry registry, final io.fd.vpp.jvpp.JVpp jvpp) throws java.io.IOException {
        super(jvpp, registry, new java.util.HashMap<>());
        java.util.Objects.requireNonNull(registry, "JVppRegistry should not be null");
        registry.register(jvpp, new FutureJVpp${plugin_name}FacadeCallback(getRequests(), eventRegistry));
    }

    @Override
    public $plugin_package.notification.${plugin_name}EventRegistry getEventRegistry() {
        return eventRegistry;
    }

$methods
}
''')


def _generate_future_jvpp_facade_methods(model):
    methods = []
    for msg in model.messages:
        if is_control_ping(msg) or is_control_ping_reply(msg):
            # Skip control_ping managed by jvpp registry.
            continue
        template = None
        if is_request(msg):
            template = _FUTURE_JVPP_FACADE_REQUEST_TEMPLATE
        elif is_dump(msg):
            template = _FUTURE_JVPP_FACADE_DUMP_TEMPLATE
        else:
            continue

        methods.append(template.substitute(
            plugin_package=model.plugin_package,
            method_name=msg.java_name_lower,
            reply_name=msg.reply_java,
            request_name=msg.java_name_upper
        ))
    return "".join(methods)

_FUTURE_JVPP_FACADE_REQUEST_TEMPLATE = Template('''
    @Override
    public java.util.concurrent.CompletionStage<${plugin_package}.dto.${reply_name}> ${method_name}(${plugin_package}.dto.${request_name} request) {
        return send(request);
    }
''')

_FUTURE_JVPP_FACADE_DUMP_TEMPLATE = Template('''
    @Override
    public java.util.concurrent.CompletionStage<${plugin_package}.dto.${reply_name}ReplyDump> ${method_name}(${plugin_package}.dto.${request_name} request) {
        return send(request, new ${plugin_package}.dto.${reply_name}ReplyDump());
    }
''')


def _generate_future_jvpp_callback(work_dir, model):
    with open("%s/FutureJVpp%sFacadeCallback.java" % (work_dir, model.plugin_java_name), "w") as f:
        f.write(_FUTURE_JVPP_CALLBACK_TEMPLATE.substitute(
            plugin_package=model.plugin_package,
            json_filename=model.json_api_files,
            plugin_name=model.plugin_java_name,
            methods=_generate_future_jvpp_callback_methods(model)
        ))

_FUTURE_JVPP_CALLBACK_TEMPLATE = Template("""
package $plugin_package.future;

/**
 * <p>Async facade callback setting values to future objects
 * <br>It was generated by jvpp_future_facade_gen.py based on $json_filename.
 */
public final class FutureJVpp${plugin_name}FacadeCallback implements $plugin_package.callback.JVpp${plugin_name}GlobalCallback {

    private final java.util.Map<java.lang.Integer, java.util.concurrent.CompletableFuture<? extends io.fd.vpp.jvpp.dto.JVppReply<?>>> requests;
    private final $plugin_package.notification.Global${plugin_name}EventCallback notificationCallback;
    private static final java.util.logging.Logger LOG = java.util.logging.Logger.getLogger(FutureJVpp${plugin_name}FacadeCallback.class.getName());

    public FutureJVpp${plugin_name}FacadeCallback(
        final java.util.Map<java.lang.Integer, java.util.concurrent.CompletableFuture<? extends io.fd.vpp.jvpp.dto.JVppReply<?>>> requestMap,
        final $plugin_package.notification.Global${plugin_name}EventCallback notificationCallback) {
        this.requests = requestMap;
        this.notificationCallback = notificationCallback;
    }

    @Override
    @SuppressWarnings("unchecked")
    public void onError(io.fd.vpp.jvpp.VppCallbackException reply) {
        final java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<?>> completableFuture;

        synchronized(requests) {
            completableFuture = (java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<?>>) requests.get(reply.getCtxId());
        }

        if(completableFuture != null) {
            completableFuture.completeExceptionally(reply);

            synchronized(requests) {
                requests.remove(reply.getCtxId());
            }
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public void onControlPingReply(final io.fd.vpp.jvpp.dto.ControlPingReply reply) {
        java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<?>> completableFuture;

        final int replyId = reply.context;
        synchronized(requests) {
            completableFuture = (java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<?>>) requests.get(replyId);

            if(completableFuture != null) {
                // Finish dump call
                if (completableFuture instanceof io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture) {
                    completableFuture.complete(((io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture) completableFuture).getReplyDump());
                    // Remove future mapped to dump call context id
                    requests.remove(((io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture) completableFuture).getContextId());
                } else {
                    // reply to regular control ping, complete the future
                    completableFuture.complete(reply);
                }
                requests.remove(replyId);
            } else {
                // future not yet created by writer, create new future, complete it and put to map under ping id
                completableFuture = new java.util.concurrent.CompletableFuture<>();
                completableFuture.complete(reply);
                requests.put(replyId, completableFuture);
            }
        }
    }

$methods
}
""")


def _generate_future_jvpp_callback_methods(model):
    methods = []
    for msg in model.messages:
        if is_control_ping(msg) or is_control_ping_reply(msg):
            # Skip control_ping managed by jvpp registry.
            continue
        if is_dump(msg) or is_request(msg):
            continue

        # Generate callbacks for all messages except for dumps and requests (handled by vpp, not client).
        template = None
        request_dto = None
        if is_details(msg):
            template = _FUTURE_JVPP_FACADE_DETAILS_CALLBACK_TEMPLATE
            request_dto = msg.request_java
        elif is_reply(msg):
            template = _FUTURE_JVPP_FACADE_REPLY_CALLBACK_TEMPLATE
            request_dto = msg.request_java
        elif is_event(msg):
            template = _FUTURE_JVPP_FACADE_EVENT_CALLBACK_TEMPLATE
        else:
            raise TypeError("Unknown message type %s", msg)

        methods.append(template.substitute(
            plugin_package=model.plugin_package,
            callback_dto=msg.java_name_upper,
            request_dto=request_dto,
            callback_dto_field=msg.java_name_lower,
        ))
    return "".join(methods)


_FUTURE_JVPP_FACADE_DETAILS_CALLBACK_TEMPLATE = Template("""
    @Override
    @SuppressWarnings("unchecked")
    public void on$callback_dto(final $plugin_package.dto.$callback_dto reply) {
        io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture<$plugin_package.dto.${callback_dto}ReplyDump> completableFuture;
        final int replyId = reply.context;
        if (LOG.isLoggable(java.util.logging.Level.FINE)) {
            LOG.fine(java.lang.String.format("Received $callback_dto event message: %s", reply));
        }
        synchronized(requests) {
            completableFuture = (io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture<$plugin_package.dto.${callback_dto}ReplyDump>) requests.get(replyId);

            if(completableFuture == null) {
                // reply received before writer created future,
                // create new future, and put into map to notify sender that reply is already received,
                // following details replies will add information to this future
                completableFuture = new io.fd.vpp.jvpp.future.AbstractFutureJVppInvoker.CompletableDumpFuture<>(replyId,
                    new $plugin_package.dto.${callback_dto}ReplyDump());
                requests.put(replyId, completableFuture);
            }
            completableFuture.getReplyDump().$callback_dto_field.add(reply);
        }
    }
""")

_FUTURE_JVPP_FACADE_REPLY_CALLBACK_TEMPLATE = Template("""
    @Override
    @SuppressWarnings("unchecked")
    public void on$callback_dto(final $plugin_package.dto.$callback_dto reply) {
        java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<$plugin_package.dto.$request_dto>> completableFuture;
        final int replyId = reply.context;
        if (LOG.isLoggable(java.util.logging.Level.FINE)) {
            LOG.fine(java.lang.String.format("Received $callback_dto event message: %s", reply));
        }
        synchronized(requests) {
            completableFuture =
            (java.util.concurrent.CompletableFuture<io.fd.vpp.jvpp.dto.JVppReply<$plugin_package.dto.$request_dto>>) requests.get(replyId);

            if(completableFuture != null) {
                // received reply on request, complete future created by sender and remove it from map
                completableFuture.complete(reply);
                requests.remove(replyId);
            } else {
                // reply received before writer created future,
                // create new future, complete it and put into map to
                // notify sender that reply is already received
                completableFuture = new  java.util.concurrent.CompletableFuture<>();
                completableFuture.complete(reply);
                requests.put(replyId, completableFuture);
            }
        }
    }
""")

_FUTURE_JVPP_FACADE_EVENT_CALLBACK_TEMPLATE = Template("""
    @Override
    public void on$callback_dto($plugin_package.dto.$callback_dto notification) {
        if (LOG.isLoggable(java.util.logging.Level.FINE)) {
            LOG.fine(java.lang.String.format("Received $callback_dto event message: %s", notification));
        }
        notificationCallback.on$callback_dto(notification);
    }
""")
