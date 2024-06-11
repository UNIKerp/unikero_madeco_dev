# -*- coding: utf-8 -*
from odoo.tests import tagged, Form
from .common import TestPeEdiCommon

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestEdiXmls(TestPeEdiCommon):

    def test_invoice_simple_case(self):
        with freeze_time(self.frozen_today):
            move = self._create_invoice().with_context(edi_test_mode=True)
            move.action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_refund_simple_case(self):
        with freeze_time(self.frozen_today):
            move = self._create_refund()
            (move.reversed_entry_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_refund_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_debit_note_simple_case(self):
        with freeze_time(self.frozen_today):
            move = self._create_debit_note()
            (move.debit_origin_id + move).action_post()

            generated_files = self._process_documents_web_services(move, {'pe_ubl_2_1'})
            self.assertTrue(generated_files)
            zip_edi_str = generated_files[0]
            edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

            current_etree = self.get_xml_tree_from_string(edi_xml)
            expected_etree = self.get_xml_tree_from_string(self.expected_debit_note_xml_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_invoice_payment_term_detraction_case(self):
        """ Invoice in USD with detractions and multiple payment term lines"""
        self.product.l10n_pe_withhold_percentage = 10
        self.product.l10n_pe_withhold_code = '001'
        with freeze_time(self.frozen_today):
            update_vals_dict = {"l10n_pe_edi_operation_type": "1001",
                                "invoice_payment_term_id": self.env.ref("account.account_payment_term_advance_60days").id}
            invoice = self._create_invoice(**update_vals_dict).with_context(edi_test_mode=True)
            invoice.action_post()

        generated_files = self._process_documents_web_services(invoice, {'pe_ubl_2_1'})
        self.assertTrue(generated_files)
        zip_edi_str = generated_files[0]
        edi_xml = self.edi_format._l10n_pe_edi_unzip_edi_document(zip_edi_str)

        current_etree = self.get_xml_tree_from_string(edi_xml)
        expected_etree = self.get_xml_tree_from_string(self.expected_invoice_xml_values)
        expected_etree = self.with_applied_xpath(
            expected_etree,
            '''
                <xpath expr="//InvoiceTypeCode" position="attributes">
                    <attribute name="listID">1001</attribute>
                </xpath>
                <xpath expr="//Note[1]" position="after">
                    <Note languageLocaleID="2006">Leyenda: Operacion sujeta a detraccion</Note>
                </xpath>
                <xpath expr="//PaymentTerms" position="replace"/>
                <xpath expr="//AccountingCustomerParty" position="after">
                    <PaymentMeans>
                        <ID>Detraccion</ID>
                        <PaymentMeansCode>999</PaymentMeansCode>
                        <PayeeFinancialAccount>
                            <ID>CUENTAPRUEBA</ID>
                        </PayeeFinancialAccount>
                    </PaymentMeans>
                    <PaymentTerms>
                        <ID>Detraccion</ID>
                        <PaymentMeansID>001</PaymentMeansID>
                        <PaymentPercent>10.0</PaymentPercent>
                        <Amount currencyID="PEN">472.00</Amount>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Credito</PaymentMeansID>
                        <Amount currencyID="USD">8496.00</Amount>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Cuota001</PaymentMeansID>
                        <Amount currencyID="USD">1888.00</Amount>
                        <PaymentDueDate>2017-01-01</PaymentDueDate>
                    </PaymentTerms>
                    <PaymentTerms>
                        <ID>FormaPago</ID>
                        <PaymentMeansID>Cuota002</PaymentMeansID>
                        <Amount currencyID="USD">6608.00</Amount>
                        <PaymentDueDate>2017-03-02</PaymentDueDate>
                    </PaymentTerms>
                </xpath>
            ''')
        self.assertXmlTreeEqual(current_etree, expected_etree)
