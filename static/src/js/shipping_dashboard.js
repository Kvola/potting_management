/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PottingShippingDashboard extends Component {
    static template = "potting_management.ShippingDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            orders: {
                draft: 0,
                confirmed: 0,
                in_progress: 0,
                done: 0,
            },
            transitOrders: {
                draft: 0,
                lots_generated: 0,
                in_progress: 0,
                ready_validation: 0,
                done: 0,
            },
            recentOrders: [],
            recentTransitOrders: [],
            productStats: [],
            totalTonnage: 0,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Load customer orders counts
        const orderStates = ['draft', 'confirmed', 'in_progress', 'done'];
        for (const state of orderStates) {
            const count = await this.orm.searchCount("potting.customer.order", [['state', '=', state]]);
            this.state.orders[state] = count;
        }

        // Load transit orders counts
        const otStates = ['draft', 'lots_generated', 'in_progress', 'ready_validation', 'done'];
        for (const state of otStates) {
            const count = await this.orm.searchCount("potting.transit.order", [['state', '=', state]]);
            this.state.transitOrders[state] = count;
        }

        // Load recent customer orders
        this.state.recentOrders = await this.orm.searchRead(
            "potting.customer.order",
            [],
            ["name", "customer_id", "date_order", "total_tonnage", "state"],
            { limit: 5, order: "create_date desc" }
        );

        // Load recent transit orders
        this.state.recentTransitOrders = await this.orm.searchRead(
            "potting.transit.order",
            [],
            ["name", "consignee_id", "product_type", "tonnage", "progress_percentage", "state"],
            { limit: 10, order: "create_date desc" }
        );

        // Load product statistics
        const productTypes = ['cocoa_mass', 'cocoa_butter', 'cocoa_cake', 'cocoa_powder'];
        const productLabels = {
            'cocoa_mass': 'Masse de cacao',
            'cocoa_butter': 'Beurre de cacao',
            'cocoa_cake': 'Cake de cacao',
            'cocoa_powder': 'Poudre de cacao'
        };
        
        this.state.productStats = [];
        for (const type of productTypes) {
            const orders = await this.orm.searchRead(
                "potting.transit.order",
                [['product_type', '=', type], ['state', '!=', 'cancelled']],
                ["tonnage"]
            );
            const totalTonnage = orders.reduce((sum, o) => sum + o.tonnage, 0);
            this.state.productStats.push({
                type: type,
                label: productLabels[type],
                count: orders.length,
                tonnage: totalTonnage
            });
        }

        // Total tonnage
        this.state.totalTonnage = this.state.productStats.reduce((sum, p) => sum + p.tonnage, 0);
    }

    openCustomerOrders(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Commandes clients',
            res_model: 'potting.customer.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openTransitOrders(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Ordres de Transit',
            res_model: 'potting.transit.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openTransitOrdersByProduct(productType) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Ordres de Transit',
            res_model: 'potting.transit.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [['product_type', '=', productType]],
            context: {},
        });
    }

    createCustomerOrder() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle commande',
            res_model: 'potting.customer.order',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    createTransitOrder() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvel OT',
            res_model: 'potting.transit.order',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'confirmed': 'Confirmée',
            'in_progress': 'En cours',
            'done': 'Terminée',
            'lots_generated': 'Lots générés',
            'ready_validation': 'Prêt validation',
            'cancelled': 'Annulée'
        };
        return labels[state] || state;
    }

    getStateBadgeClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'confirmed': 'bg-info',
            'in_progress': 'bg-warning',
            'done': 'bg-success',
            'lots_generated': 'bg-primary',
            'ready_validation': 'bg-info',
            'cancelled': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getProductTypeLabel(type) {
        const labels = {
            'cocoa_mass': 'Masse',
            'cocoa_butter': 'Beurre',
            'cocoa_cake': 'Cake',
            'cocoa_powder': 'Poudre'
        };
        return labels[type] || type;
    }
}

registry.category("actions").add("potting_shipping_dashboard", PottingShippingDashboard);
