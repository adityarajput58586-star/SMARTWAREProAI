"""Utility functions for smart inventory management"""
from datetime import datetime
from flask import current_app
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def suggest_storage_locations(product_name, quantity_needed, db, preferred_section_id=None, product_id=None):
    """
    Intelligently suggest storage locations with overflow handling
    
    Strategy:
    1. If preferred section specified, try to use it first
    2. If section can't fit all, try to extend section capacity (if warehouse space available)
    3. If can't extend, overflow to adjacent/nearby sections
    4. Track overflow with labels
    
    Returns list of tuples: (section, quantity_to_store, overflow_info)
    """
    from models import WarehouseSection, WarehouseConfig, SectionCapacityLog
    
    suggestions = []
    remaining_quantity = quantity_needed
    
    # Get warehouse config
    config = WarehouseConfig.query.first()
    if not config:
        config = WarehouseConfig(total_space=1000)
        db.session.add(config)
        db.session.commit()
    
    # Get all sections
    sections = WarehouseSection.query.order_by(WarehouseSection.id).all()
    
    if not sections:
        return [(None, quantity_needed, "No sections found. Please create warehouse sections first.")]
    
    # If preferred section specified, handle it specially
    if preferred_section_id:
        preferred_section = WarehouseSection.query.get(preferred_section_id)
        
        if preferred_section:
            available_in_preferred = preferred_section.available_space
            shortage = remaining_quantity - available_in_preferred
            
            # Case 1: Preferred section can fit everything as-is
            if available_in_preferred >= remaining_quantity:
                suggestions.append((preferred_section, remaining_quantity, None))
                return suggestions
            
            # Case 2: Check if we can extend the section to fit everything
            if shortage > 0 and config.available_space >= shortage:
                # Extend the section capacity to fit all units
                old_capacity = preferred_section.capacity
                preferred_section.capacity += shortage
                
                # Log the capacity change
                capacity_log = SectionCapacityLog(
                    section_id=preferred_section.id,
                    old_capacity=old_capacity,
                    new_capacity=preferred_section.capacity,
                    change_amount=shortage,
                    reason=f"Auto-extended to accommodate {product_name}",
                    product_id=product_id
                )
                db.session.add(capacity_log)
                db.session.commit()
                
                # Now store everything in the extended section
                suggestions.append((
                    preferred_section, 
                    remaining_quantity, 
                    f"✨ Section {preferred_section.name} auto-extended by {shortage} units to accommodate all stock"
                ))
                remaining_quantity = 0
                return suggestions
            
            # Case 3: Can't extend enough, use available space and overflow
            if available_in_preferred > 0:
                suggestions.append((preferred_section, available_in_preferred, None))
                remaining_quantity -= available_in_preferred
            
            # Case 4: Overflow to other sections
            if remaining_quantity > 0:
                # Find adjacent/nearby sections (next in line)
                overflow_sections = [s for s in sections if s.id != preferred_section.id and s.available_space > 0]
                
                for overflow_section in overflow_sections:
                    if remaining_quantity <= 0:
                        break
                    
                    available = overflow_section.available_space
                    if available > 0:
                        to_store = min(available, remaining_quantity)
                        suggestions.append((
                            overflow_section, 
                            to_store, 
                            f"⚠️ Overflow from {preferred_section.name} → stored in {overflow_section.name}"
                        ))
                        remaining_quantity -= to_store
    
    # If no preferred section or still have remaining quantity, use smart placement
    if remaining_quantity > 0:
        # Find sections with available space
        available_sections = [s for s in sections if s.available_space > 0]
        
        for section in available_sections:
            if remaining_quantity <= 0:
                break
            
            available = section.available_space
            if available > 0:
                to_store = min(available, remaining_quantity)
                suggestions.append((section, to_store, None))
                remaining_quantity -= to_store
    
    # If still have remaining quantity, suggest creating new section
    if remaining_quantity > 0:
        if config.available_space >= remaining_quantity:
            suggestions.append((
                None, 
                remaining_quantity, 
                f"💡 Create new section with {remaining_quantity} units capacity (warehouse has {config.available_space} units available)"
            ))
        else:
            suggestions.append((
                None, 
                remaining_quantity, 
                f"❌ Insufficient warehouse space! Need {remaining_quantity} units but only {config.available_space} available. Consider expanding warehouse or removing unused sections."
            ))
    
    return suggestions

def send_low_stock_alert(product, recipients, db):
    """
    Send low stock alert to managers, admins, and vendors
    recipients: dict with keys 'managers', 'admins', 'vendors'
    Only sends to valid email addresses
    """
    from models import NotificationLog
    
    print(f"📨 send_low_stock_alert called for product: {product.name}")
    
    subject = f"⚠️ Low Stock Alert: {product.name}"
    
    # Prepare message content
    current_qty = product.quantity
    threshold_qty = product.threshold_quantity
    percentage = (current_qty / threshold_qty * 100) if threshold_qty > 0 else 0
    
    message_body = f"""
    Low Stock Alert
    
    Product: {product.name}
    Current Quantity: {current_qty} {product.unit_type}
    Threshold: {threshold_qty} {product.unit_type} ({product.threshold_percentage}%)
    Current Level: {percentage:.1f}% of threshold
    
    Action Required:
    - Managers: Please review and place order if needed
    - Vendor: Please prepare stock for potential order
    
    This is an automated alert from SmartWare Pro Inventory System.
    """
    
    notifications_sent = []
    
    print(f"📧 Processing recipients: {recipients}")
    
    # Send to managers and admins (ALWAYS log notification)
    for recipient_type in ['managers', 'admins']:
        if recipient_type in recipients:
            for email in recipients[recipient_type]:
                print(f"  → Processing {recipient_type[:-1]}: {email}")
                # Validate email before sending
                if not is_valid_email(email):
                    print(f"⚠️  Invalid {recipient_type[:-1]} email: {email}")
                    # Still log the notification attempt
                    log = NotificationLog(
                        product_id=product.id,
                        notification_type='low_stock',
                        recipient_email=email,
                        recipient_type=recipient_type[:-1],
                        message=message_body,
                        status='invalid_email'
                    )
                    db.session.add(log)
                    continue
                
                # Try to send email
                success = send_email(email, subject, message_body)
                
                # ALWAYS log notification regardless of email success
                log = NotificationLog(
                    product_id=product.id,
                    notification_type='low_stock',
                    recipient_email=email,
                    recipient_type=recipient_type[:-1],  # Remove 's'
                    message=message_body,
                    status='sent' if success else 'failed'
                )
                db.session.add(log)
                print(f"  ✓ Notification logged: {email} - status: {'sent' if success else 'failed'}")
                notifications_sent.append((email, success))
    
    # Send to vendor if exists (ALWAYS log notification)
    if product.vendor:
        vendor_email = product.vendor.email
        print(f"  → Processing vendor: {vendor_email}")
        
        vendor_message = f"""
        Low Stock Alert - Prepare Stock
        
        Product: {product.name}
        Current Quantity: {current_qty} {product.unit_type}
        Threshold: {threshold_qty} {product.unit_type}
        
        {"AUTO-REORDER ENABLED: Please prepare to ship stock automatically." if product.auto_reorder_enabled else "Please standby for potential order from warehouse manager."}
        
        This is an automated alert from SmartWare Pro Inventory System.
        """
        
        if is_valid_email(vendor_email):
            success = send_email(vendor_email, subject, vendor_message)
            
            # ALWAYS log notification
            log = NotificationLog(
                product_id=product.id,
                notification_type='vendor_alert',
                recipient_email=vendor_email,
                recipient_type='vendor',
                message=vendor_message,
                status='sent' if success else 'failed'
            )
            db.session.add(log)
            print(f"  ✓ Vendor notification logged: {vendor_email} - status: {'sent' if success else 'failed'}")
            notifications_sent.append((vendor_email, success))
        else:
            print(f"⚠️  Invalid vendor email: {vendor_email}")
            # Still log the notification attempt
            log = NotificationLog(
                product_id=product.id,
                notification_type='vendor_alert',
                recipient_email=vendor_email,
                recipient_type='vendor',
                message=vendor_message,
                status='invalid_email'
            )
            db.session.add(log)
            print(f"  ✓ Vendor notification logged: {vendor_email} - status: invalid_email")
    
    db.session.commit()
    print(f"✅ All notifications committed to database. Total sent: {len(notifications_sent)}")
    return notifications_sent

def send_auto_reorder_notification(product, vendor, db):
    """
    Send automatic reorder notification to vendor
    Only sends if vendor has valid email address
    """
    from models import NotificationLog
    
    subject = f"🔄 Auto-Reorder: {product.name}"
    
    message_body = f"""
    Automatic Reorder Request
    
    Product: {product.name}
    Current Quantity: {product.quantity} {product.unit_type}
    Suggested Reorder Quantity: {int(product.threshold_quantity * 2)} {product.unit_type}
    
    This is an AUTOMATIC reorder. Please prepare and ship the stock.
    
    Warehouse: SmartWare Pro
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    This is an automated request from SmartWare Pro Inventory System.
    """
    
    # Validate vendor email and ALWAYS log notification
    if not is_valid_email(vendor.email):
        print(f"⚠️  Invalid vendor email: {vendor.email}")
        log = NotificationLog(
            product_id=product.id,
            notification_type='auto_reorder',
            recipient_email=vendor.email,
            recipient_type='vendor',
            message=message_body,
            status='invalid_email'
        )
        db.session.add(log)
        db.session.commit()
        return False
    
    success = send_email(vendor.email, subject, message_body)
    
    # ALWAYS log notification regardless of email success
    log = NotificationLog(
        product_id=product.id,
        notification_type='auto_reorder',
        recipient_email=vendor.email,
        recipient_type='vendor',
        message=message_body,
        status='sent' if success else 'failed'
    )
    db.session.add(log)
    db.session.commit()
    
    return success

def is_valid_email(email):
    """
    Validate email address format
    Returns True if email looks valid, False otherwise
    """
    import re
    if not email:
        return False
    # Basic email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def send_email(to_email, subject, body):
    """
    Send email using SMTP (Gmail)
    Reads configuration from environment variables or app config
    Validates email address before attempting to send
    """
    import os
    import socket
    
    # Validate email address first
    if not is_valid_email(to_email):
        print(f"⚠️  Skipping invalid email address: {to_email}")
        return False
    
    try:
        # Get SMTP configuration from environment
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('EMAIL_USER')  # Use EMAIL_USER consistently
        smtp_password = os.environ.get('EMAIL_PASSWORD')  # Use EMAIL_PASSWORD consistently
        
        # If no SMTP credentials, just log to console and return success
        if not smtp_user or not smtp_password:
            print(f"\n{'='*60}")
            print(f"📧 EMAIL NOTIFICATION (Console Mode - No SMTP Configured)")
            print(f"{'='*60}")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}")
            print(f"{'='*60}")
            print(f"⚠️  To send real emails, configure SMTP settings in .env file")
            print(f"{'='*60}\n")
            return True
        
        # Create HTML email
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb; border-radius: 10px;">
                    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                        <h1 style="color: white; margin: 0;">📦 SmartWare Pro</h1>
                        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0;">Warehouse Management System</p>
                    </div>
                    <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h2 style="color: #6366f1; margin-top: 0;">{subject}</h2>
                        <div style="white-space: pre-line; color: #4b5563;">
{body}
                        </div>
                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
                        <p style="color: #9ca3af; font-size: 12px; text-align: center; margin: 0;">
                            This is an automated notification from SmartWare Pro<br>
                            Please do not reply to this email
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"SmartWare Pro <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email with timeout
        print(f"📧 Attempting to send email to {to_email}...")
        
        # Set socket timeout to prevent hanging (5 seconds)
        socket.setdefaulttimeout(5)
        
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=5)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except socket.timeout:
        print(f"⏱️  SMTP connection timeout for {to_email} - Email service may be blocked")
        return False
    except socket.error as e:
        print(f"🔌 Network error sending email to {to_email}: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"📧 SMTP error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error sending email to {to_email}: {e}")
        return False
    finally:
        # Reset socket timeout to default
        socket.setdefaulttimeout(None)

def check_and_trigger_alerts(product, db):
    """
    Check if product is below threshold and trigger appropriate alerts
    """
    try:
        # Calculate threshold
        threshold_qty = product.threshold_quantity
        current_qty = product.quantity
        
        # Debug info
        print(f"\n{'='*60}")
        print(f"🔍 CHECKING ALERTS FOR: {product.name}")
        print(f"{'='*60}")
        print(f"Current Quantity: {current_qty} {product.unit_type}")
        print(f"Threshold Percentage: {product.threshold_percentage}%")
        print(f"Threshold Quantity: {threshold_qty} {product.unit_type}")
        print(f"Is Below Threshold: {product.is_below_threshold}")
        
        # Get historical max for reference
        historical_quantities = [h.new_quantity for h in product.stock_history] if product.stock_history else []
        all_quantities = historical_quantities + [current_qty]
        max_qty = max(all_quantities) if all_quantities else current_qty
        print(f"Maximum Quantity Ever: {max_qty} {product.unit_type}")
        print(f"{'='*60}\n")
        
        if not product.is_below_threshold:
            print(f"✅ Stock level OK - No alert needed\n")
            return False
        
        print(f"⚠️  ALERT TRIGGERED - Stock below threshold!\n")
        
        # Get manager and admin emails from AuthorizedUser database
        from models import AuthorizedUser
        
        managers = [user.email for user in AuthorizedUser.query.filter_by(role='manager', is_active=True).all()]
        admins = [user.email for user in AuthorizedUser.query.filter_by(role='admin', is_active=True).all()]
        
        print(f"📧 Recipients - Managers: {managers}, Admins: {admins}")
        
        recipients = {
            'managers': managers,
            'admins': admins,
            'vendors': []
        }
        
        # Send low stock alert
        send_low_stock_alert(product, recipients, db)
        
        # If auto-reorder is enabled and vendor exists, send auto-reorder
        if product.auto_reorder_enabled and product.vendor:
            print(f"🔄 Auto-reorder enabled, sending to vendor: {product.vendor.email}")
            send_auto_reorder_notification(product, product.vendor, db)
            return True
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in check_and_trigger_alerts: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_section_usage(db):
    """
    Recalculate current usage for all warehouse sections based on stock batches
    """
    from models import WarehouseSection, StockBatch
    
    sections = WarehouseSection.query.all()
    
    for section in sections:
        total_usage = db.session.query(db.func.sum(StockBatch.quantity)).filter_by(
            section_id=section.id
        ).scalar() or 0
        
        section.current_usage = total_usage
    
    db.session.commit()

def reduce_stock_from_batches(product, quantity_to_reduce, db):
    """
    Reduce stock from batches using FIFO (First In, First Out)
    Returns list of affected sections for tracking
    """
    from models import StockBatch
    
    remaining_to_reduce = quantity_to_reduce
    affected_sections = []
    
    # Get batches ordered by arrival date (FIFO - oldest first)
    batches = StockBatch.query.filter_by(product_id=product.id).order_by(
        StockBatch.arrival_date.asc()
    ).all()
    
    for batch in batches:
        if remaining_to_reduce <= 0:
            break
        
        if batch.quantity > 0:
            # Calculate how much to reduce from this batch
            reduction = min(batch.quantity, remaining_to_reduce)
            batch.quantity -= reduction
            remaining_to_reduce -= reduction
            
            affected_sections.append({
                'section': batch.section.name,
                'reduced': reduction
            })
            
            # If batch is empty, delete it
            if batch.quantity == 0:
                db.session.delete(batch)
    
    return affected_sections
